"""
Application entry point for the UPS monitor.
"""

import time

from logger import logger
from monitor import UPSMonitor
from ups_uart import UPSUART
from power_monitor import PowerMonitor
from shutdown_controller import ShutdownController


def main() -> None:
    """Start and run the UPS monitor."""
    logger.info("Starting UPS monitor.")

    monitor = None
    uart = None
    power_monitor = None

    try:

        shutdown_controller = ShutdownController()

        monitor = UPSMonitor(shutdown_controller)
        uart = UPSUART()
        power_monitor = PowerMonitor(shutdown_controller)

        logger.info("UPS monitor started.")

        while not shutdown_controller.shutdown_started:
            status = uart.read_status()

            if status is not None:
                power_monitor.update(status)
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("UPS monitor interrupted by user.")

    except Exception:
        logger.exception("Unexpected error in UPS monitor.")

    finally:
        if uart is not None:
            uart.close()

        if monitor is not None:
            monitor.close()

        logger.info("UPS monitor stopped.")

if  __name__ == "__main__":
    main()