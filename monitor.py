"""

UPS GPIO monitor.

State machine:
    NORMAL  
    │
    │ Rising edge
    ▼
    CONFIRMING
    │
    │ Falling edge
    ▼
    检查 HIGH 持续时间
    │
    ├── 不满足 → NORMAL
    │
    └── 满足 → SHUTDOWN_REQUESTED
                        │
                        ▼
                safe_shutdown()
"""

import time
import threading
from enum import Enum, auto
from typing import Optional

from gpiozero import DigitalInputDevice

from config import(
    CONFIRM_DELAY_SECONDS,
    POWER_LOSS_SIGNAL
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
    def __init__(self, pin: int):

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

        logger.info(
            "Initializing UPS monitor: GPIO=%d",
            self.pin
        )

        # GPIO input
        # Internal pull-down
        # LOW = NORMAL
        # HIGH = power-loss signal
        self.device = DigitalInputDevice(
            pin=self.pin,
            pull_up=False
        )

        # =====================================================
        # GPIO callbacks
        # =====================================================

        self.device.when_pressed = self._on_rising_edge
        self.device.when_released = self._on_falling_edge

        logger.info(
            "UPS monitor initialized:",
            "GPIO%d, pull_down enabled.",
            self.pin
        )

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
            if self.device.is_active:
                logger.warning(
                    "GPIO%d is HIGH at startup.",
                    self.pin
                )

            else:
                logger.info(
                    "GPIO%d is LOW at startup;",
                    "UPS power is considered normal",
                    self.pin
                )
        except Exception:
            logger.exception("Failed to determine GPIO state at startup.")

    def _on_rising_edge(self) -> None:       
        """Handle LOW -> HIGH transition"""

        with self.state_lock:

            logger.warning(
                "GPIO%d rising edge detected:",
                "LOW -> HIGH",
                self.pin
            )

            # Already shutting down.
            if self.state == MonitorState.SHUTDOWN_REQUESTED:
                logger.warning(
                    "Rising edge ignored:"
                    "shutdown already requested."
                )
                return

            # Shutdown already failed.
            if self.state == MonitorState.SHUTDOWN_FAILED:
                logger.warning(
                    "Rising edge ignored:"
                    "previous shutdown attempt failed."
                )
                return

            # Already confirming
            if self.state == MonitorState.CONFIRMING:
                logger.debug(
                    "Rising edge ignored:"
                    "confirmation already in progress."
                )
                return

            # Normal --> Confirming
            self.state = MonitorState.CONFIRMING

            self.power_loss_start_time = time.monotonic()

            logger.warning(
                "Power-loss signal started,"
                "waiting for falling edge."
            )

    def _on_falling_edge(self) -> None:
        """Handle HIGH -> LOW transition"""

        with self.state_lock:

            logger.info(
                "GPIO%d falling edge detected:",
                "HIGH -> LOW",
                self.pin
            )

            if self.state != MonitorState.CONFIRMING:
                logger.info(
                    "Falling edge ignored:"
                    "current state is %s",
                    self.state.name
                )
                return

            if self.power_loss_start_time is None:
                logger.warning(
                    "Falling edge detected without "
                    "a vaild rising-edge timestamp."
                )

                self.state = MonitorState.NORMAL
                return

            duration = (time.monotonic - self.power_loss_start_time)
            self.power_loss_start_time = None

            logger.info(
                "Power-loss signal duration: %.3f seconds.",
                duration
            )

            if duration < CONFIRM_DELAY_SECONDS:
                self.state = MonitorState.NORMAL

                logger.info(
                    "Power-loss signal too short,"
                    "shutdown cancelled."
                )
                return
            
            # Confirmed
            self.state = MonitorState.SHUTDOWN_REQUESTED

            logger.critical(
                "UPS power loss confirmed:",
                "signal duration %.3f seconds.",
                duration
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

        try:
            self.device.close()
        except Exception:
            logger.exception("Failed to close GPIO device.")

        logger.info("UPS monitor closed.")