"""

System-level operations for UPS monitor.

This module is responsible only for interacting with the
Linux operating system.

Responsibilities:
    - Synchronize filesystem buffers
    - Execute system shutdown
    - Report command failures

It does not:
    - Monitor GPIO
    - Decide whether power loss is confirmed
    - Manage UPS states

"""

import time
import subprocess
from collections.abc import Sequence

from config import (
    SHUTDOWN_COMMAND, 
    SYNC_COMMAND, 
    WAIT_SECONDS,
    SHUTDOWN_MAX_RETRIES,
    SHUTDOWN_RETRY_DELAY_SECONDS
)
from logger import logger

# ============================================================
# Constants
# ============================================================

# Maximum time allowed for a system command.
#
# This prevents the UPS monitor from being blocked forever
# if a command hangs.
COMMAND_TIMEOUT_SECONDS = 5.0

# ============================================================
# Command execution
# ============================================================

def run_command(
        command: Sequence[str],
        timeout: float = COMMAND_TIMEOUT_SECONDS
) -> bool:
    """
    Execute a system command.

    Args:
        command: Command and arguments, for example:
                 ["sudo", "sync"]
        timeout: Maximum execution time in seconds.

    Returns:
        True if the command exits with return code 0.
        False if execution fails.
    """

    command_text = " ".join(command)

    logger.info("Executing command: %s", command_text)

    try:
        result = subprocess.run(
            command,
            check=False,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.TimeoutExpired:
        logger.error(
            "Command timed out after %.1f seconds: %s",
            timeout,
            command_text
        )
        return False
    except FileNotFoundError:
        logger.exception("Command not found: %s", command_text)
        return False
    except PermissionError:
        logger.exception(
            "Permission denied while executiong: %s",
            command_text
        )
        return False
    except OSError:
        logger.exception(
            "OS error while executiong: %s",
            command_text
        )
        return False
    except Exception:
        logger.exception(
            "Unexpected error while executing: %s",
            command_text
        )
        return False

    if result.returncode != 0:
        logger.error(
            "Command failed: %s, return code=%d",
            command_text,
            result.returncode
        )
        if result.stdout:
            logger.error(
                "stdout: %s",
                result.stdout.strip()
            )
        if result.stderr:
            logger.error(
                "stderr: %s",
                result.stderr.strip()
            )

        return False

    # ============================================================
    # Successful command
    # ============================================================

    if result.stdout:
        logger.debug(
            "stdout: %s",
            result.stdout.strip()
        )
    if result.stderr:
        logger.debug(
            "stderr: %s",
            result.stderr.strip()
        )

    logger.info(
        "Command completed successfully: %s",
        command_text
    )

    return True

# ============================================================
# Filesystem synchronization
# ============================================================

def sync_filesystem() -> bool:
    """

    Synchronize filesystem buffers to disk.

    Returns:
        True if sync succeeds,  otherwise False.
    """

    logger.info("Synchronizing filesystem")

    res = run_command(SYNC_COMMAND)

    if res:
        logger.info("Filesystem synchronization completed.")
    else:
        logger.error("Filesystem synchronization failed.")

    return res

# ============================================================
# System shutdown
# ============================================================

def shutdown_system() -> bool:
    """
    
    Request system shutdown.

    The shutdown command will be attempted up to
    SHUTDOWN_MAX_RETRIES times.

    Returns:
        True if the shutdown command was successfully started.
        False if the command could not be  executed.
    """

    for attempt in range(1, SHUTDOWN_MAX_RETRIES + 1):

        logger.warning(
            "Shutdown attempt %d/%d",
            attempt,
            SHUTDOWN_MAX_RETRIES
        )

        res = run_command(SHUTDOWN_COMMAND)

        if res:
            logger.warning(
                "Shutdown command succeeded on attempt %d/%d",
                attempt,
                SHUTDOWN_MAX_RETRIES
            )

            return True
        
        # ====================================================
        # Shutdown failed
        # ====================================================
        logger.error(
            "Shutdown attempt %d/%d failed",
            attempt,
            SHUTDOWN_MAX_RETRIES
        )
        # No need to wait after the final attempt.
        if attempt < SHUTDOWN_MAX_RETRIES:
            logger.warning(
                "Retrying shutdown in %.1f seconds",
                SHUTDOWN_RETRY_DELAY_SECONDS
            )

            time.sleep(SHUTDOWN_RETRY_DELAY_SECONDS)
    # ========================================================
    # All attempts failed
    # ========================================================
    logger.critical(
        "Shutdown failed after %d attempts",
        SHUTDOWN_MAX_RETRIES
    )
    
    return False

# ============================================================
# Safe shutdown
# ============================================================

def safe_shutdown() -> bool:
    """
    
    Perform a safe shutdown sequence.
    
    Sequence:
        1. sync filesystem
        2. wait
        3. attempt shutdown up to N times

    Returns:
        True if shutdown was successfully requested.
        False if shutdown failed.
    """

    logger.warning("Starting safe shutdown sequence")

    # Step 1: Sync filesystem
    if not sync_filesystem():
        logger.critical(
            "Safe shutdown aborted because filesystem"
            "synchronization failed"
        )
        return False

    # Step 2: Wait before shutdown
    if WAIT_SECONDS > 0:
        logger.info(
            "Waiting %.1f seconds before shutdown",
            WAIT_SECONDS
        )
        time.sleep(WAIT_SECONDS)

    # Step 3: Shutdown with retry
    if not shutdown_system():
        logger.critical(
            "Safe shutdown failed after all retries."
        )

        return False

    logger.critical("Shutdown command successfully issued.")

    return True