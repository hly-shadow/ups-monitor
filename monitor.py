"""

UPS GPIO monitor.

State machine:
    Normal
      |
      | power loss detected
      |
      ⋁
    Confirming
      |
      | power restored before timeout
      +---------------------> Normal
      |
      | power loss confirmed
      ⋁
    Shutdown Requested
      |
      | safe_shutdown()
      |
      +---------------------> Shutdown command issued

If all shutdown attempts fail:
    Shutdown Requested
      |
      | shutdown failed
      ⋁
    Shutdown_Failed
      |
      | power restored
      ⋁
    Normal
"""

import threading
from enum import Enum, auto
from typing import Optional

from gpiozero import Button

from config import(
    CONFIRM_DELAY_SECONDS,
    POWER_LOSS_SIGNAL,
    SHUTDOWN_PIN
)
from logger import logger
from system import safe_shutdown

# ============================================================
# State
# ============================================================

class MonitorState(Enum):
    """
    UPS monitor states.
    """

    # UPS power is normal
    NORMAL = auto()

    # Power loss detected, waiting for confirmation.
    CONFIRMING = auto()

    # Power loss confirmed and shutdown has been requested.
    SHUTDOWN_REQUESTED = auto()

    # Shutdown was attempted but all retries failed.
    SHUTDOWN_FAILED = auto()

# ============================================================
# UPS Monitor
# ============================================================

class UPSMonitor():
    """
    
    Monitor UPS power status through a GPIO input.

    The monitor does not execute GPIO polling manually.
    gpiozero callbacks are used for state changes.
    """
    def __init__(self, pin: int = SHUTDOWN_PIN):

        self.pin = pin

        # =====================================================
        # State
        # =====================================================
        self.state = MonitorState.NORMAL

        # Protect state and timer from concurrent access.
        #
        # GPIO callbacks and threading.Timer callbacks can
        # execute in different threads.
        self.state_lock = threading.Lock()

        # Timer used during the confirmation period.
        self.confirm_timer: Optional[threading.Timer] = None

        # =====================================================
        # GPIO confirmation
        # =====================================================
        self.active_level = POWER_LOSS_SIGNAL.active_state
        self.pull_up = POWER_LOSS_SIGNAL.pull_up

        logger.info(
            "Initializing UPS monitor:"
            " GPIO=%d, signal=%s, active_state=%s, pull_up=%s",
            self.pin,
            POWER_LOSS_SIGNAL.name,
            self.active_level,
            self.pull_up
        )

        self.device = Button(
            pin=self.pin,
            active_state=self.active_level,
            pull_up=self.pull_up
        )

        # =====================================================
        # GPIO callbacks
        # =====================================================

        self.device.when_pressed = ()
        self.device.when_released = ()

        logger.info("UPS monitor initialized.")

        # =====================================================
        # Check startup state
        # =====================================================

        self._check_initial_state()

    # ============================================================
    # Startup
    # ============================================================

    def _check_initial_state(self) -> None:
        """
        
        Check GPIO state when the monitor starts.

        This is important because the Raspberry Pi may boot while
        UPS power is already lost.

        In that case,there may be no new GPIO edge after startup,so
        we must explicitly check the current state.
        """

        try:
            if self.device.is_pressed:
                logger.warning("UPS power loss detected at startup.")

                self._on_power_loss_detected()

            else:
                logger.info("UPS power is normal at startup.")
        except Exception:
            logger.exception("Failed to determine UPS state at startup.")

    # Power loss
    def _on_power_loss_detected(self) -> None:       
        """
        
        Handle UPS power loss.

        Start a confirmation timer.

        If power is restored before the timer expires,
        the timer will be cancelled.
        """

        with self.state_lock:

            # Already shutting down.
            if self.state == MonitorState.SHUTDOWN_REQUESTED:
                logger.warning(
                    "Power loss event ignored:"
                    "shutdown already requested."
                )
                return

            # Shutdown already failed.
            if self.state == MonitorState.SHUTDOWN_FAILED:
                logger.warning(
                    "Power loss event ignored:"
                    "previous shutdown attempt failed."
                )
                return

            # Already confirming
            if self.state == MonitorState.CONFIRMING:
                logger.debug(
                    "Power loss event ignored:"
                    "confirmation already in progress."
                )
                return

            # Normal --> Confirming
            self.state = MonitorState.CONFIRMING

            logger.warning(
                "UPS power loss detected,"
                "starting %.1f seconds confirmation period",
                CONFIRM_DELAY_SECONDS
            )

            self.confirm_timer = threading.Timer(CONFIRM_DELAY_SECONDS, self._confirm_power_loss)

            # Do not prevent Python from exiting if the main
            # thread is terminated.
            self.confirm_timer.daemon = True

            self.confirm_timer.start()

    # Power loss confirmation
    def _confirm_power_loss(self) -> None:
        """
        
        Confirm that UPS power is still lost.

        This method is executed by threading.Timer.
        """

        with self.state_lock:
            # Timer may have been cancelled.
            if self.state != MonitorState.CONFIRMING:
                logger.info(
                    "Power loss confirmation ignored:"
                    "state is %s",
                    self.state.name
                )

                self.confirm_timer = None
                return

            # Confirmed
            self.state = MonitorState.SHUTDOWN_REQUESTED

            self.confirm_timer = None

            logger.critical(
                "UPS power loss confirmed after %.1f seconds.",
                CONFIRM_DELAY_SECONDS
            )
            logger.critical("Shutdown requested.")

        # -------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT execute safe_shutdown() while holding 
        # state_lock
        #
        # safe_shutdown() can take several seconds.
        # -------------------------------------------------
        self._execute_shutdown()

    # Power restored
    def _on_power_restored(self) -> None:
        """
        
        Handle UPS power restoration.

        If restoration occurs during the confirmation period,
        cancel the pending shutdown.

        If shutdown has already been requested, restoration
        does NOT cancel it. 
        """

        with  self.state_lock:
            # Shutdown already requested
            if self.state == MonitorState.SHUTDOWN_REQUESTED:
                logger.warning(
                    "UPS power restored, but shutdown has"
                    "already  been requested."
                )
                return

            # Shutdown failed
            if self.state == MonitorState.SHUTDOWN_FAILED:
                logger.warning("UPS power restored after failed shutdown.")

                self.state = MonitorState.NORMAL
                logger.info("UPS monitor returned to NORMAL state.")

                return
            
            # Unexpected restoration
            if self.state != MonitorState.CONFIRMING:
                logger.info(
                    "UPS power restored "
                    "(no shutdown confirmation pending)"
                )

                self.state = MonitorState.NORMAL

                return

            # Cancel confirmation
            if self.confirm_timer is not None:
                self.confirm_timer.cancel()
                self.confirm_timer = None

            self.state = MonitorState.NORMAL
            
            logger.info(
                "UPS power restored within confirmation period,"
                "shutdown cancelled."
            )

    def _execute_shutdown(self) -> None:
        """Execute the safe shutdown sequence."""

        logger.critical("Executing safe shutdown.")

        try:
            res = safe_shutdown()
        except Exception:
            logger.exception("Unexcepted exception during safe shutdown.")
            res = False

        if res:
            logger.critical("Safe shutdown completed successfully.")

            # Keep SHUTDOWN_REQUESTED
            #
            # The shutdown command has already been issued.
            # A later power-restored event must not cancel it.
            return
        
        # Shutdown failed
        #
        # Do not return directly to NORMAL here.If the UPS 
        # signal remains active,there may be no new GPIO event
        # to trigger another transition.
        with self.state_lock:
            self.state = MonitorState.SHUTDOWN_FAILED

        logger.critical("Safe shutdown failed after all retry attempts.")

    def close(self) -> None:
        """Close the UPS monitor and release GPIO resources."""

        logger.info("Close the UPS monitor.")

        with self.state_lock:
            if self.confirm_timer is not None:
                self.confirm_timer.cancel()
                self.confirm_timer = None
        try:
            self.device.close()
        except Exception:
            logger.exception("Failed to close GPIO device.")

        logger.info("UPS monitor closed.")