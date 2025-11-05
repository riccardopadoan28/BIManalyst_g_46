"""
Read/parse helpers:
- CSV loading
- Text normalization
- EU decimal parsing
"""

import csv
import unicodedata
from typing import Dict, List


def read_price_list(csv_path: str, delimiter: str = ";", encoding: str = "cp1252") -> List[Dict[str, str]]:
    """Read CSV into a list of dicts using provided delimiter and encoding."""
    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [row for row in reader]


def normalize_text(s: str) -> str:
    """Lowercase, strip diacritics, collapse spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.strip().lower().split())


def parse_decimal_eu(value: str) -> float:
    """Parse strings with EU style decimals (1.234,56 -> 1234.56)."""
    s = str(value or "").strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def build_price_index_by_text(rows: List[Dict[str, str]], text_col: str = "Text") -> Dict[str, Dict[str, str]]:
    """Create a normalized index by description text."""
    idx: Dict[str, Dict[str, str]] = {}
    for r in rows:
        key = normalize_text(r.get(text_col, ""))
        if key:
            idx[key] = r
    return idx
