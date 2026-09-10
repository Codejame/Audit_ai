"""Utility helper functions for number parsing, financial arithmetic, and hashing."""
import hashlib
import re
from typing import Any, Optional, Tuple, Union

def parse_financial_number(value: Any) -> Optional[float]:
    """
    Parses strings, ints, or floats into float numbers.
    Handles:
    - Bracketed negative accounting format: '(12,500.00)' -> -12500.0
    - Negative with minus sign: '-12,500.00' or '- 12500' -> -12500.0
    - Currency symbols: '$12,500.00', '₹ 6,862.00', 'USD 12500'
    - Dashes/empty: '-' -> 0.0 or None depending on context
    - Commas and whitespace
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    raw = str(value).strip()
    if not raw or raw in ("-", "--", "N/A", "n/a", "nil", "null"):
        return 0.0

    # Check for bracketed negative (accounting format) e.g., (1,018,904,990)
    is_negative = False
    bracket_match = re.match(r"^\((.+)\)$", raw)
    if bracket_match:
        is_negative = True
        raw = bracket_match.group(1).strip()
    elif raw.startswith("-"):
        is_negative = True
        raw = raw.lstrip("-").strip()

    # Remove currency symbols and non-numeric chars except dot and digits
    # Keep digits, dot
    cleaned = re.sub(r"[^\d.]", "", raw)
    if not cleaned:
        return None

    try:
        num = float(cleaned)
        return -num if is_negative else num
    except ValueError:
        return None

def numbers_approx_equal(
    val1: Optional[float],
    val2: Optional[float],
    tolerance: float = 1.0
) -> Tuple[bool, float]:
    """
    Compares two values with a tolerance threshold.
    Returns (is_match, variance).
    """
    if val1 is None or val2 is None:
        return False, 0.0
    variance = round(abs(val1 - val2), 2)
    return variance <= tolerance, variance

def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 hash of bytes."""
    return hashlib.sha256(content).hexdigest()
