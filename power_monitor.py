"""
Power monitor.

UART provides:
    Vin
    BATCAP
    Vout

This module implements an additional software protection layer
based on UPS output voltage.

STA remains the independent vendor protection mechanism.
"""

import time
from typing import Optional

from config import (
    VOUT_WARNING_THRESHOLD_MV,
    VOUT_SHUTDOWN_THRESHOLD_MV,
    VOUT_SHUTDOWN_CONFIRM_SECONDS,
    VOUT_RECOVERY_THRESHOLD_MV,
    LOG_UART_STATUS,
    VOLTAGE_CHANGE_THRESHOLD_MV,
    SIMULATE_VOUT,
    SIMULATED_VOUT_MV_SEQUENCE
)

from logger import logger
from ups_uart import UPSStatus
from shutdown_controller import ShutdownController
from simulator import VoltageSimulator

class PowerMonitor:

    def __init__(self, shutdown_controller: ShutdownController):

        self.shutdown_controller = shutdown_controller

        self.last_status: Optional[UPSStatus] = None

        self.low_voltage_since: Optional[float] = None

        self.voltage_simulator = VoltageSimulator(SIMULATED_VOUT_MV_SEQUENCE)


    def update(self, status: UPSStatus) -> None:

        if SIMULATE_VOUT:

            status = UPSStatus(
                input_power=status.input_power,
                battery_capacity=status.battery_capacity,
                output_voltage_mv=self.voltage_simulator.get_voltage()
            )

        now = time.monotonic()

        self._log_status(status)

        self._check_output_voltage(status, now)

        self.last_status = status

    def _log_status(self, status: UPSStatus) -> None:

        if not LOG_UART_STATUS:
            return

        logger.info(
            "UPS status: Vin=%s, BATCAP=%d%%, Vout=%dmV",
            "GOOD" if status.input_power else "NG",
            status.battery_capacity,
            status.output_voltage_mv
        )

    def _check_output_voltage(self, status: UPSStatus, now: float) -> None:

        voltage = status.output_voltage_mv

        if self.last_status is not None:

            delta = abs(voltage - self.last_status.output_voltage_mv)
            print(f"delta={delta}")
            if delta >= VOLTAGE_CHANGE_THRESHOLD_MV:
                logger.info(
                    "UPS output voltage changed: %dmV -> %dmV",
                    self.last_status.output_voltage_mv,
                    voltage
                )

        if voltage <= VOUT_WARNING_THRESHOLD_MV:

            if self.low_voltage_since is None:

                logger.warning(
                    "UPS output voltage LOW: %dmV (warning threshold=%dmV)",
                    voltage,
                    VOUT_WARNING_THRESHOLD_MV
                )

        if voltage >= VOUT_RECOVERY_THRESHOLD_MV:

            if self.low_voltage_since is not None:
                duration = now - self.low_voltage_since

                logger.info(
                    "UPS output voltage recovered: %dmV after %.2f seconds.",
                    voltage,
                    duration
                )
            self.low_voltage_since = None
            return

        if voltage <= VOUT_SHUTDOWN_THRESHOLD_MV:

            if self.low_voltage_since is None:

                self.low_voltage_since = now

                logger.critical(
                    "UPS output voltage below shutdown threshold: %dmV <= %dmV",
                    voltage,
                    VOUT_SHUTDOWN_THRESHOLD_MV
                )
                logger.critical(
                    "Starting %.1f second low-voltage confirmation.",
                    VOUT_SHUTDOWN_CONFIRM_SECONDS
                )
                return

            duration = now - self.low_voltage_since

            logger.warning(
                "UPS low voltage persists: %.2f / %.2f seconds.",
                duration,
                VOUT_SHUTDOWN_CONFIRM_SECONDS
            )

            if duration >= VOUT_SHUTDOWN_CONFIRM_SECONDS:
                self.shutdown_controller.request_shutdown(
                    f"UPS output voltage too low: {voltage}mV"
                )
