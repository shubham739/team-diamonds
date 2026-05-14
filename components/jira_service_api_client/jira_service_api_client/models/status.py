from enum import Enum


class Status(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    TO_DO = "to_do"

    def __str__(self) -> str:
        return str(self.value)
