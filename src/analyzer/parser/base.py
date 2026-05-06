"""
Base parser interface.

All format-specific parsers inherit from BaseParser and implement
the `parse` method. This plugin architecture allows easy extension
for new bill formats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from analyzer.models.schemas import Transaction


class BaseParser(ABC):
    """Abstract base class for all bill parsers.

    Each parser handles a specific bill format (WeChat, Alipay, etc.)
    and converts raw data into standardized Transaction objects.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable parser name."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """List of supported file extensions."""
        ...

    @abstractmethod
    def parse(self, filepath: str | Path) -> list[Transaction]:
        """Parse a bill file into a list of Transaction objects.

        Args:
            filepath: Path to the bill file.

        Returns:
            List of standardized Transaction objects.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is not supported or corrupted.
        """
        ...

    @abstractmethod
    def can_handle(self, filepath: str | Path) -> bool:
        """Check if this parser can handle the given file.

        Uses header detection or format sniffing — does NOT rely
        solely on file extension.

        Args:
            filepath: Path to the file to check.

        Returns:
            True if this parser can process the file.
        """
        ...

    def _read_file(self, filepath: str | Path, encoding: str = "utf-8") -> str:
        """Read file content with encoding fallback."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Try primary encoding first, then common alternatives
        encodings = [encoding, "utf-8-sig", "gbk", "gb2312", "latin-1"]
        for enc in encodings:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue

        raise ValueError(f"Cannot decode file {filepath} with any supported encoding")
