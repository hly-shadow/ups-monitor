"""

UPS GPIO monitor
"""

import time
import threading
from enum import Enum, auto
from typing import Optional

from gpiozero import DigitalInputDevice

from config import(
    SHUTDOWN_PIN,
    STA_MIN_PULSE_SECONDS,
    STA_MAX_PULSE_SECONDS
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
    
    Monitor UPS STA/Halt signal on GPIO SHUTDWON_PIN(BCM).

    Vendor behavior:
        Normal:
            GPIO SHUTDWON_PIN(BCM) -> LOW
        Halt:
            GPIO SHUTDWON_PIN(BCM) -> High for approximately 2~3 seconds
        Then:
            GPIO SHUTDWON_PIN(BCM) -> LOW
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

        self.power_loss_start_time: Optional[float] = None

        # =====================================================
        # GPIO confirmation
        # =====================================================

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

        self.device.when_activated = self._on_rising_edge
        self.device.when_deactivated = self._on_falling_edge

        logger.info(
            "UPS monitor initialized:",
            "GPIO%d, internal pull-down enabled.",
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

        Important:
            STA is normal LOW.

        If GPIO is HIGH at startup, we do NOT immediately
        shutdown because we don't know whether this is a 
        complete STA pulse or simply a startup condition.
        """

        try:
            if self.device.is_active:
                logger.warning(
                    "GPIO%d is HIGH at startup.",
                    self.pin
                )

            else:
                logger.info(
                    "GPIO%d is LOW at startup; STA inactive.",
                    self.pin
                )
        except Exception:
            logger.exception("Failed to determine GPIO state at startup.")

    def _on_rising_edge(self) -> None:       
        """
        LOW -> HIGH

        Start measuring STA pulse duration.
        """

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
                "STA/Halt pulse started,"
                "waiting for falling edge."
            )

    def _on_falling_edge(self) -> None:
        """
        HIGH -> LOW
        
        Calculate STA pulse duration.
        """

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
                    "a valid rising-edge timestamp."
                )

                self.state = MonitorState.NORMAL
                return

            duration = (time.monotonic() - self.power_loss_start_time)
            self.power_loss_start_time = None

            logger.info(
                "STA/Halt signal duration: %.3f seconds.",
                duration
            )

            # Too short
            if duration < STA_MIN_PULSE_SECONDS:

                self.state = MonitorState.NORMAL

                logger.warning(
                    "STA pulse too short: %.3f < %.3f seconds",
                    duration,
                    STA_MIN_PULSE_SECONDS
                )
                return

            # Too long
            if duration > STA_MAX_PULSE_SECONDS:

                self.state = MonitorState.NORMAL

                logger.warning(
                    "STA pulse too long: %.3f > %.3f seconds",
                    duration,
                    STA_MAX_PULSE_SECONDS
                )
                return

            # Confirmed
            self.state = MonitorState.SHUTDOWN_REQUESTED

            logger.info(
                "Valid STA/Halt signal confirmed: %.3f seconds.",
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
    
    def _execute_shutdown(self) -> None:
        """Execute the safe shutdown sequence."""

        logger.info("Executing safe shutdown requested by UPS STA.")

        try:
            res = safe_shutdown()
        except Exception:
            logger.exception("Unexpected exception during safe shutdown.")
            res = False

        if res:
            logger.info("Safe shutdown completed successfully.")

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
            logger.critical(
                "Safe shutdown failed after all retry attempts.",
                "Monitor entering terminal state."
            )

    def close(self) -> None:
        """Close the UPS monitor and release GPIO resources."""

        logger.info("Close the UPS monitor.")

        try:
            self.device.close()
        except Exception:
            logger.exception("Failed to close GPIO device.")

        logger.info("UPS monitor closed.")