from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionTimestamp:
    start_time: datetime = datetime.now()

    @classmethod
    def get_timestamp(cls):
        return cls.start_time.strftime("%Y%m%d_%H%M%S")
