"""

UART is not responsible for shutdown; it is only responsible for 
reading status: 
    Vin GOOD / NG
    BATCAP
    Vout
"""

import re
import serial
from dataclasses import dataclass
from typing import Optional

from config import(
    UART_DEVICE,
    UART_BAUDRATE,
    UART_BYTESIZE,
    UART_PARITY,
    UART_STOPBITS,
    UART_TIMEOUT,
    UART_BUFFER_MAX_SIZE,
    UART_FRAME_MAX_SIZE
)
from logger import logger

@dataclass
class UPSStatus:
    input_power: bool
    battery_capacity: float
    output_voltage_mv: float

class UPSUART:
    """
    
    Read SmartUPS V3.2P UART status.

    Example frame:
        $ SmartUPS V3.2P,Vin GOOD,BATCAP 100,Vout 5250 $
    or
        $ SmartUPS V3.2P,Vin NG,BATCAP 100,Vout 5250 $
    """

    FRAME_PATTERN = re.compile(
        r"\$\s*"
        r"SmartUPS\s+V[\d\.]+P,"
        r"Vin\s+(GOOD|NG),"
        r"BATCAP\s+(\d+),"
        r"Vout\s+(\d+)"
        r"\s*\$",
        re.IGNORECASE
    )

    def __init__(self):

        self.serial = serial.Serial(
            port=UART_DEVICE,
            baudrate=UART_BAUDRATE,
            bytesize=UART_BYTESIZE,
            parity=UART_PARITY,
            stopbits=UART_STOPBITS,
            timeout=UART_TIMEOUT
        )

        self.buffer = ""

        logger.info(
            "UPS UART initialized: %s %d 8N1",
            UART_DEVICE,
            UART_BAUDRATE
        )

    def _parse_frame(self, frame: str) -> Optional[UPSStatus]:

        match = self.FRAME_PATTERN.fullmatch(frame.strip())

        if not match:
            logger.warning(
                "Invalid  UPS UART frame: %r",
                frame
            )

            return None

        vin = match.group(1).upper()
        battery_capacity = float(match.group(2))
        output_voltage = float(match.group(3))

        if not 0<= battery_capacity <=100:
            return None
        if not 0< output_voltage <10000:
            return None

        status = UPSStatus(
            input_power=(vin == "GOOD"),
            battery_capacity=battery_capacity,
            output_voltage_mv=output_voltage
        )

        return status

    def _append_data(self, data: bytes) -> None:
        """Append UART data while keeping the buffer bounded."""

        if not data:
            return

        text = data.decode("ascii", errors="ignore")

        self.buffer += text

        if len(self.buffer) > UART_BUFFER_MAX_SIZE:
            logger.warning(
                "UART receive buffer exceeded %d bytes; discarding old data.",
                UART_BUFFER_MAX_SIZE
            )
            # Keep only the newest data.
            self.buffer = self.buffer[-(UART_BUFFER_MAX_SIZE-1):]

    def _extract_frame(self) -> Optional[str]:
        """
        Extract one complete $...$ frame.

        Returns:
            Complete frame, or None if incomplete.
        """

        start = self.buffer.find("$")
        # No start marker yet.
        if start == -1:
            if len(self.buffer) > UART_FRAME_MAX_SIZE:
                logger.warning(
                    "Discarding %d bytes without frame marker.",
                    len(self.buffer)
                )
                self.buffer = ""
            return None

        # Discard garbage before '$'
        if start > 0:
            prefix = self.buffer[:start]

            if prefix.strip():
                logger.warning(
                    "Discarding %d bytes before frame start.",
                    start
                )
            self.buffer = self.buffer[start:]
        # Find the next '$'
        end = self.buffer.find("$", 1)
        if end == -1:
            # Frame is incomplete
            if len(self.buffer) > UART_FRAME_MAX_SIZE:
                logger.warning(
                    "Incomplete UART frame exceeded %d bytes; discarding frame.",
                    UART_FRAME_MAX_SIZE
                )
                # Discard current malformed frame
                self.buffer = self.buffer[1:]
            return None

        frame = self.buffer[:end + 1]

        self.buffer = self.buffer[end + 1:]

        return frame

    def read_status(self) -> Optional[UPSStatus]:
        """
        Read and parse one valid UPS status frame.

        Invalid frames are discarded.
        Incomplete frames remain in the buffer.
        """

        try:
            data = self.serial.read(
                self.serial.in_waiting or 1
            )

            self._append_data(data)

            while True:

                frame = self._extract_frame()

                if frame is None:
                    return None

                status = self._parse_frame(frame)

                if status is not None:
                    return status

                # Invalid frame:
                # continue looking for the next frame.
        except serial.SerialException:
            logger.exception(
                "UPS UART communication error."
            )
            return None
        except Exception:
            logger.exception(
                "Unexpected UPS UART error."
            )
            return None
        
    def close(self):

        try:
            self.serial.close()

        except Exception:
            logger.exception(
                "Failed to close UPS UART."
            )