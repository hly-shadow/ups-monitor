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
    STA_PULL_UP,
    STA_ACTIVE_STATE,
    STA_CONFIRM_SECONDS
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
    
    Monitor the UPSPack V3P STA signal.

    V3P STA protocol:
        LOW -> normal
        HIGH -> System Halt request

    Once a valid Halt signal is detected, safe_shutdown() is
    executed only once.   
    """
    def __init__(self):

        self._shutdown_triggered = False
        self._lock = threading.Lock()
        self._confirm_timer = None

        # =====================================================
        # GPIO confirmation
        # =====================================================

        self.device = DigitalInputDevice(
            pin=SHUTDOWN_PIN,
            pull_up=STA_PULL_UP,
            # active_state=STA_ACTIVE_STATE,
            bounce_time=0.05
        )

        # =====================================================
        # GPIO callbacks
        # =====================================================

        self.device.when_activated = self._on_sta_activated
        self.device.when_deactivated = self._on_sta_deactivated

        logger.info(
            "UPS STA monitor started:"
            "GPIO%d, normal=LOW, halt=HIGH.",
            SHUTDOWN_PIN
        )

        logger.info(
            "Initial STA state: %s",
            "HIGH" if self.device.is_active else "LOW"
        )

        # Important:
        # If the program starts while STA is already HIGH,
        # when_activated may not be called because there is
        # no LOW -> HIGH transition.
        if self.device.is_active:
            logger.warning(
                "STA is already HIGH startup; "
                "starting Halt confirmation."
            )
            self._start_confirmation()

    # ============================================================
    # Startup
    # ============================================================

    def _start_confirmation(self) -> None:
        """
        Start a short confirmation timer.

        STA must remain HIGH for STA_CONFIRM_SECONDS.
        """

        with self._lock:
            if self._shutdown_triggered:
                logger.info(
                    "Shutdown already triggered; "
                    "ignoring STA signal."
                )
                return
            
            if self._confirm_timer is not None:
                logger.info("STA confirmation already in progress.")
                return

            logger.warning(
                "STA HIGH detected; "
                "waiting %.3f seconds for confirmation.",
                STA_CONFIRM_SECONDS
            )

            self._confirm_timer = threading.Timer(
                STA_CONFIRM_SECONDS,
                self._confirm_sta
            )

            self._confirm_timer.daemon = True
            self._confirm_timer.start()

    def _cancel_confirmation(self) -> None:
        """
        Cancel confirmation if STA returns LOW
        before confirmation completes.
        """

        with self._lock:
            if self._confirm_timer is not None:
                logger.info(
                    "STA returned LOW before confirmation; "
                    "shutdown cancelled."
                )

                self._confirm_timer.cancel()
                self._confirm_timer = None
    def _confirm_sta(self) -> None:
        """
        Verify that STA is still HIGH after the 
        confirmation period.
        """

        with self._lock:
            self._confirm_timer = None

            if self._shutdown_triggered:
                return

            if not self.device.is_active:
                logger.info(
                    "STA confirmation failed: "
                    "signal is LOW."
                )
                return

            logger.critical("UPS STA Halt signal confirmed.")

            # This prevents duplicate shutdown requests.
            self._shutdown_triggered = True
        try:
            res = safe_shutdown()

            if res:
                logger.info("Safe shutdown command executed successfully.")
            else:
                logger.critical("Safe shutdown failed.")
        except Exception:
            logger.exception("Exception while executing shutdown!")

    def _on_sta_activated(self) -> None:       
        """
        Called when STA changes from LOW -> HIGH
        """

        logger.warning("STA signal changed: LOW -> HIGH")

        self._start_confirmation()

    def _on_sta_deactivated(self) -> None:
        """
        Called when STA changes from HIGH -> LOW
        """

        logger.info("STA signal changed: HIGH -> LOW")        

        self._cancel_confirmation()
    
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

        logger.info("Closing the UPS monitor.")

        with self._lock:
            if self._confirm_timer is not None:
                self._confirm_timer.cancel()
                self._confirm_timer = None

        try:
            self.device.when_activated = None
            self.device.when_deactivated = None
            self.device.close()
        except Exception:
            logger.exception("Failed to close GPIO device.")

        logger.info("UPS monitor closed.")