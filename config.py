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

# Vendor STA behavior
# normal = LOW 
# halt = HIGH
STA_PULL_UP = False

# High pulse singnal duration: 2-3 seconds.
STA_MIN_PULSE_SECONDS = 2.0
SAT_MAX_PULSE_SECONDS = 3.0

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

SHUTDOWN_COMMAND_TIMEOUT = 10.0

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
