import ifcopenshell as ifc
import csv
import unicodedata
from typing import Dict, List


def read_price_list(csv_path: str, delimiter: str = ";", encoding: str = "cp1252") -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [row for row in reader]


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.strip().lower().split())


def parse_decimal_eu(value: str) -> float:
    s = str(value or "").strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def build_price_index_by_text(rows: List[Dict[str, str]], text_col: str = "Text") -> Dict[str, Dict[str, str]]:
    idx: Dict[str, Dict[str, str]] = {}
    for r in rows:
        key = normalize_text(r.get(text_col, ""))
        if key:
            idx[key] = r
    return idx
