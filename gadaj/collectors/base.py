from abc import ABC, abstractmethod
from datetime import datetime


class Collector(ABC):
    """
    One source of work evidence.

    To add a new source:
      1. Create gadaj/collectors/<name>.py
      2. Subclass Collector and implement collect() and source_name
      3. Register the new collector in cli.py

    No other files need to change.
    """

    @abstractmethod
    def collect(self, since: datetime, until: datetime) -> list:
        """
        Return a list of model instances covering the given window.
        Both datetimes are UTC-aware. Implementations must filter to this
        window; they must not assume the caller will filter.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable label used in output section headers."""
        ...

    @property
    def available(self) -> bool:
        """
        Return False if this source is not usable in the current environment.
        cli.py skips unavailable collectors with a soft warning.
        Default: True. Override when availability is not guaranteed.
        """
        return True
