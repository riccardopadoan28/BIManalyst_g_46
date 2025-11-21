"""
Read/parse helpers:
- CSV loading
- Text normalization
- EU decimal parsing

Functions:
- read_price_list: Read CSV into a list of dicts using provided delimiter and encoding
- normalize_text: Lowercase, strip diacritics, collapse spaces for consistent text comparison
- parse_decimal_eu: Parse strings with EU style decimals (1.234,56 -> 1234.56)
- build_price_index_by_text: Create a normalized index by description text for fast lookup
"""
from collections import defaultdict
import csv
import unicodedata
from typing import Dict, List

# Read CSV into a list of dicts using provided delimiter and encoding.
def read_price_list(csv_path: str, delimiter: str = ";", encoding: str = "cp1252") -> List[Dict[str, str]]:
    """Read CSV into a list of dicts using provided delimiter and encoding."""
    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [row for row in reader]

# Lowercase, strip diacritics, collapse spaces for consistent text comparison.
# Used for fuzzy matching between IFC element names and price list descriptions.
def normalize_text(s: str) -> str:
    """Lowercase, strip diacritics, collapse spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.strip().lower().split())

# Parse strings with EU style decimals (1.234,56 -> 1234.56).
# Handles European number format where dot is thousands separator and comma is decimal.
def parse_decimal_eu(value: str) -> float:
    """Parse strings with EU style decimals (1.234,56 -> 1234.56)."""
    s = str(value or "").strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)

# Create a normalized index by description text for fast lookup.
# Maps normalized text keys to their corresponding CSV rows.
def build_price_index_by_text(rows: List[Dict[str, str]], text_col: str = "Text") -> Dict[str, Dict[str, str]]:
    """Create a normalized index by description text."""
    idx: Dict[str, Dict[str, str]] = {}
    for r in rows:
        key = normalize_text(r.get(text_col, ""))
        if key:
            idx[key] = r
    return idx
