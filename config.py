"""
UPS Monitor configuration

This file contains configuration only.
Do not put monitor logic here.

"""

from enum import Enum
from pathlib import Path

# ============================================================
# Application
# ============================================================

APP_NAME = "ups-monitor"
APP_VERSION = "1.0.0"

# ============================================================
# GPIO configuration
# ============================================================

# BCM GPIO number.
# GPIO 17 = physical pin 11 on Raspberry Pi 4B.
SHUTDOWN_PIN = 17

class PowerLossSignal(Enum):
    """GPIO level that represents UPS power loss."""

    HIGH = (True, False)
    LOW = (False, True)

    def __init__(self, active_state: bool, pull_up: bool):
        self.active_state = active_state
        self.pull_up = pull_up

# Which GPIO level means "UPS power lost".
#
# "HIGH":
#       GPIO becomes HIGH when UPS power is lost.
#
# "LOW":
#       GPIO  becomes LOW when UPS power is lost.
# 
# You must choose the value according to your actual UPS.
# signal circuit.
POWER_LOSS_ACTIVE_LEVEL = "HIGH"

# ============================================================
# Power-loss confirmation
# ============================================================

# Power must remain lost for this amount of time before
# shutdown is triggered.
#
# Example:
#   2.0 seconds:
#       power lost --> wait 2 seconds -->shutdown
#
# If power returns before 2 seconds:
#       cancel shutdown
CONFIRM_DELAY_SECONDS = 2.0

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

# ============================================================
# Validation
# ============================================================

if CONFIRM_DELAY_SECONDS <= 0:
    raise ValueError("CONFIRM_DELAY_SECONDS must be greater than 0")

if WAIT_SECONDS < 0:
    raise ValueError("WAIT_SECONDS must not be negative")