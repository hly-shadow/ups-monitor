"""
Centralized shutdown controller.

All shutdown requests from STA, UART, or other
sources must go through ShutdownController.
"""

import threading
from enum import Enum, auto
from typing import Optional

from logger import logger
from system import safe_shutdown

class ShutdownState(Enum):

    IDLE = auto()
    SHUTDOWN_REQUESTED = auto()
    SHUTDOWN_EXECUTING = auto()
    SHUTDOWN_COMPLETED = auto()
    SHUTDOWN_FAILED = auto()

class ShutdownController:

    def __init__(self):
        self._lock = threading.Lock()
        self._state = ShutdownState.IDLE
        self._reason: Optional[str] = None

    @property
    def state(self) -> ShutdownState:
        with self._lock:
            return self._state

    @property
    def shutdown_started(self) -> bool:
        with self._lock:
            return self._state != ShutdownState.IDLE

    @property
    def reason(self) -> Optional[str]:
        with self._lock:
            return  self._reason

    def request_shutdown(self, reason: str) -> bool:
        """
        Request a system shutdown.

        Returns:
            True - this call accepted the shutdown request
            False - shutdown was already requested/executed
        """

        with self._lock:
            if self._state != ShutdownState.IDLE:

                logger.warning(
                    "Shutdown request ignored: "
                    "shutdown already in progress/completed"
                    "(state=%s, reason=%s)",
                    self._state.name,
                    self._reason
                )
                return False

            self._state = ShutdownState.SHUTDOWN_REQUESTED
            self._reason = reason

            logger.warning("Shutdown requested: %s", reason)

        self._execute_shutdown()

        return True

    def _execute_shutdown(self) -> None:

        with self._lock:

            if self._state != ShutdownState.SHUTDOWN_REQUESTED:
                return

            self._state = ShutdownState.SHUTDOWN_EXECUTING

            reason = self._reason

        logger.info("Executing safe shutdown: %s", reason)

        try:
            # res = safe_shutdown()
            res = True
        except Exception:
            logger.exception("Exception during safe shutdown.")
            res = False

        with self._lock:
            if res:
                self._state = ShutdownState.SHUTDOWN_COMPLETED
                logger.info("Safe shutdown command completed.")
            else:
                self._state = ShutdownState.SHUTDOWN_FAILED
                logger.critical("Safe shutdown command failed.")
