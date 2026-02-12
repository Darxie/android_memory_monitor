"""
Execution timestamp management for test runs.
Provides singleton timestamp for consistent output directory naming.
"""
from datetime import datetime
from typing import Optional


class ExecutionTimestamp:
    """
    Manages execution timestamp for test runs.
    Uses singleton pattern to ensure consistent timestamp across all modules.
    """
    
    _start_time: Optional[datetime] = None

    @classmethod
    def get_timestamp(cls, format_string: str = "%Y%m%d_%H%M%S") -> str:
        """
        Get or create the execution timestamp.
        
        Args:
            format_string: strftime format string for timestamp
        
        Returns:
            Formatted timestamp string
        """
        if cls._start_time is None:
            cls._start_time = datetime.now()
        return cls._start_time.strftime(format_string)
    
    @classmethod
    def reset(cls) -> None:
        """Reset the timestamp to current time."""
        cls._start_time = datetime.now()
    
    @classmethod
    def get_datetime(cls) -> datetime:
        """
        Get the datetime object.
        
        Returns:
            Datetime object of execution start
        """
        if cls._start_time is None:
            cls._start_time = datetime.now()
        return cls._start_time
    
    @classmethod
    def get_human_readable(cls) -> str:
        """
        Get human-readable timestamp.
        
        Returns:
            Human-readable timestamp string
        """
        return cls.get_timestamp("%Y-%m-%d %H:%M:%S")
