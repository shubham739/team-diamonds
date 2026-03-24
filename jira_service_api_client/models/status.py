from enum import Enum


class Status(str, Enum):
    CANCELLED = "cancelled"
    COMPLETE = "complete"
    IN_PROGRESS = "in_progress"
    TODO = "todo"

    def __str__(self) -> str:
        return str(self.value)
