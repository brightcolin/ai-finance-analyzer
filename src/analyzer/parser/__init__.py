"""
Parser layer — converts raw bill files into standardized Transactions.

Usage:
    from analyzer.parser import parse_file
    transactions = parse_file("wechat_bill.csv")
"""

from __future__ import annotations

from pathlib import Path

from analyzer.models.schemas import Transaction
from analyzer.parser.base import BaseParser
from analyzer.parser.csv_generic import GenericCSVParser
from analyzer.parser.wechat import WeChatParser

# Parser registry — order matters: specific parsers first, generic last
_PARSERS: list[BaseParser] = [
    WeChatParser(),
    GenericCSVParser(),  # Fallback
]


def parse_file(filepath: str | Path) -> list[Transaction]:
    """Parse a bill file using auto-detected format.

    Iterates through registered parsers and uses the first one
    that can handle the file. Falls back to GenericCSVParser.

    Args:
        filepath: Path to the bill file.

    Returns:
        List of parsed Transaction objects.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If no parser can handle the file.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    for parser in _PARSERS:
        if parser.can_handle(path):
            return parser.parse(path)

    raise ValueError(
        f"No parser can handle file: {filepath}. "
        f"Supported formats: {get_supported_formats()}"
    )


def parse_file_with(
    filepath: str | Path, parser_name: str
) -> list[Transaction]:
    """Parse using a specific named parser."""
    for parser in _PARSERS:
        if parser.name.lower() == parser_name.lower():
            return parser.parse(filepath)

    available = [p.name for p in _PARSERS]
    raise ValueError(f"Unknown parser: '{parser_name}'. Available: {available}")


def register_parser(parser: BaseParser) -> None:
    """Register a custom parser (inserted before the generic fallback)."""
    _PARSERS.insert(-1, parser)


def get_supported_formats() -> list[str]:
    """List all supported file formats across all parsers."""
    formats = set()
    for parser in _PARSERS:
        formats.update(parser.supported_formats)
    return sorted(formats)


def list_parsers() -> list[str]:
    """List names of all registered parsers."""
    return [p.name for p in _PARSERS]


__all__ = [
    "parse_file",
    "parse_file_with",
    "register_parser",
    "get_supported_formats",
    "list_parsers",
    "BaseParser",
    "WeChatParser",
    "GenericCSVParser",
]
