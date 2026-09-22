"""
Application entry point for the UPS monitor.
"""

import time

from logger import logger
from monitor import UPSMonitor
from ups_uart import UPSUART
from config import VOLTAGE_CHANGE_THRESHOLD_MV


def main() -> None:
    """Start and run the UPS monitor."""
    logger.info("Starting UPS monitor.")

    monitor = None
    uart = None

    last_status = None

    try:

        monitor = UPSMonitor()
        uart = UPSUART()

        logger.info("UPS monitor started.")

        while True:
            status = uart.read_status()

            if status is not None:
                if last_status is None:
                    logger.info(
                        "UPS status: Vin=%s, BATCAP=%d%%, Vout=%dmV",
                        "GOOD" if status.input_power else "NG",
                        status.battery_capacity,
                        status.output_voltage_mv
                    )

                else:
                    if status.input_power != last_status.input_power:
                        logger.warning(
                            "UPS input power changed: %s -> %s",
                            "GOOD" if last_status.input_power else "NG",
                            "GOOD" if status.input_power else "NG",
                        )
                    if status.battery_capacity != last_status.battery_capacity:
                        logger.info(
                            "UPS battery capacity changed: %d%% -> %d%%",
                            last_status.battery_capacity,
                            status.battery_capacity
                        )

                    voltage_delta = abs(status.output_voltage_mv - last_status.output_voltage_mv)

                    if voltage_delta >= VOLTAGE_CHANGE_THRESHOLD_MV:
                        logger.info(
                            "UPS output voltage changed: %dmV -> %dmV",
                            last_status.output_voltage_mv,
                            status.output_voltage_mv
                        )


                last_status = status
                    
            
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