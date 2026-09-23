"""

UPS GPIO monitor
"""

import threading
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
from shutdown_controller import ShutdownController


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
    def __init__(self, shutdown_controller: ShutdownController):

        self.shutdown_controller = shutdown_controller

        # =====================================================
        # GPIO confirmation
        # =====================================================

        self.device = DigitalInputDevice(
            pin=SHUTDOWN_PIN,
            pull_up=STA_PULL_UP,
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


    def _on_sta_activated(self) -> None:       
        """
        Called when STA changes from LOW -> HIGH
        """

        logger.warning("STA signal changed: LOW -> HIGH")

        self.shutdown_controller.request_shutdown("Vendor STA Halt signal.")

    def _on_sta_deactivated(self) -> None:
        """
        Called when STA changes from HIGH -> LOW
        """

        logger.info("STA signal inactive.")        
        

    def close(self) -> None:
        """Close the UPS monitor and release GPIO resources."""

        logger.info("Closing the UPS monitor.")

        try:
            self.device.when_activated = None
            self.device.when_deactivated = None
            self.device.close()
        except Exception:
            logger.exception("Failed to close GPIO device.")

        logger.info("UPS monitor closed.")