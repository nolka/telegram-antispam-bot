from queue import Queue
from typing import Any


class DelayedResponseQueue(Queue):
    """
    Implements one-shot queue for receiving only one message, then queue will be closed
    """
    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        result = super().get(block, timeout)
        self.task_done()
        self.join()
        return result
