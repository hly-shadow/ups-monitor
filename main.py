"""
Application entry point for the UPS monitor.
"""

from signal import pause

from logger import logger
from monitor import UPSMonitor
from config import SHUTDOWN_PIN

def main() -> None:
    """Start and run the UPS monitor."""
    logger.info("Starting UPS monitor.")

    monitor = UPSMonitor(pin=SHUTDOWN_PIN)

    try:
        # Keep the process alive while gpiozero handles callbacks.
        pause()
    except KeyboardInterrupt:
        logger.info("UPS monitor interrupted by user.")

    except Exception:
        logger.exception("Unexcepted error in UPS monitor.")

    finally:
        if monitor is not None:
            monitor.close()

            logger.info("UPS monitor stopped.")

if  __name__ == "__main__":
    main()