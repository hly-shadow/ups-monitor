"""
UPS Monitor configuration

This file contains configuration only.
Do not put monitor logic here.

"""

from pathlib import Path

# ============================================================
# Application
# ============================================================

APP_NAME = "ups-monitor"
APP_VERSION = "1.0.0"

# ============================================================
# GPIO / STA
# ============================================================

# BCM GPIO number.
# GPIO 17 = physical pin 11 on Raspberry Pi 4B.
SHUTDOWN_PIN = 17

# ============================================================
# Signal detection confirmation
# ============================================================

# Vendor STA protocol:
# LOW = normal 
# HIGH = System Halt request 
STA_PULL_UP = False
STA_ACTIVE_STATE = True

# Require STA HIGH to remain stable for this long
# before triggering shutdown
STA_CONFIRM_SECONDS = 0.1

# High pulse singnal duration: 2.0-3.0 seconds.
# STA_MIN_PULSE_SECONDS = 2.0
# STA_MAX_PULSE_SECONDS = 3.0

# ============================================================
# Logging
# ============================================================
LOG_FILE = Path("./logs/ups.log")

# ============================================================
# System command
# ============================================================

# Synchronize filesystem buffers to disk before shutdown.
SYNC_COMMAND = ["sudo", "sync"]

# Shutdown command.
SHUTDOWN_COMMAND = ["sudo", "shutdown", "-h", "now"]

# Wait between sync and shutdown.
WAIT_SECONDS = 1.0

# Maximum number of shutdown attempts.
#
# For example:
#   1st attempt -> failed
#   wait
#   2nd attempt -> failed
#   wait
#   3rd attempt -> failed
#   stop retrying
SHUTDOWN_MAX_RETRIES = 3

# Delay between failed shutdown attempts.
SHUTDOWN_RETRY_DELAY_SECONDS = 1.0

# Maximum time allowed for a system command.
#
# This prevents the UPS monitor from being blocked forever
# if a command hangs.
COMMAND_TIMEOUT_SECONDS = 5.0

# ============================================================
# UART
# ============================================================

UART_DEVICE = "/dev/serial0"
UART_BAUDRATE = 9600

# UART is 8N1
UART_BYTESIZE = 8
UART_PARITY = "N"
UART_STOPBITS = 1

UART_TIMEOUT = 1.0

UART_BUFFER_MAX_SIZE = 4096
UART_FRAME_MAX_SIZE = 256


# ============================================================
# UPS Voltage Protection
# ============================================================

# Undervoltage warning
VOUT_WARNING_THRESHOLD_MV = 5100

VOUT_SHUTDOWN_THRESHOLD_MV = 5000

VOUT_SHUTDOWN_CONFIRM_SECONDS = 5.0

VOUT_RECOVERY_THRESHOLD_MV = 5150

VOLTAGE_CHANGE_THRESHOLD_MV = 5

LOG_UART_STATUS = False

# ============================================================
# Simulation / Test
# ============================================================

SIMULATE_VOUT = False

# Each element:
# (Duration in seconds, Simulated Vout in mV)

## Example:
# 3 seconds 5000mV
# 3 seconds 5250mV
SIMULATED_VOUT_MV_SEQUENCE = [
    (2.0, 5000),
    (3.0, 5250),
    (6.0, 5000)
]