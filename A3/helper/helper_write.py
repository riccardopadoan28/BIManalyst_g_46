"""
Reporting helpers:
- Build a summarized cost estimation (grouping rows)
- Write a simple CSV-like text report
"""

import os
import difflib
from typing import Dict, List, Tuple

from .helper_read import read_price_list, parse_decimal_eu
from .helper_get import get_quantity_for_unit


def _format_number_eu(value: float, decimals: int = 2) -> str:
    """Format 1234.56 as 1.234,56 (EU style)."""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _best_match(element_name: str, candidates: List[Dict[str, str]], name_col: str) -> Dict[str, str] | None:
    """Fuzzy pick the best row for an element by comparing names."""
    if not candidates:
        return None
    base = (element_name or "").strip().lower()
    scores = [
        (difflib.SequenceMatcher(None, base, (c.get(name_col) or "").strip().lower()).ratio(), c)
        for c in candidates
    ]
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[0][1] if scores else None


def build_cost_estimation_summary(
    ifc_file,
    csv_path: str,
    *,
    ident_col: str = "Identification Code",
    text_col: str = "Name",
    unit_col: str = "Measurement Unit",
    unit_cost_col: str = "IfcCostValue",
    ifc_match_col: str = "Ifc Match",
    delimiter: str = ";",
    encoding: str = "cp1252",
) -> Dict[str, object]:
    """Aggregate quantities and costs by (ident, name, unit, unit_cost)."""
    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)

    # Index rows by IFC class for quick lookup
    by_class: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        cls = (r.get(ifc_match_col) or "").strip() or "IfcElement"
        by_class.setdefault(cls, []).append(r)

    agg: Dict[Tuple[str, str, str, float], Dict[str, object]] = {}
    scanned = 0
    matched = 0

    for el in ifc_file.by_type("IfcElement"):
        scanned += 1
        candidates = by_class.get(el.is_a(), [])
        if not candidates:
            continue

        match = _best_match(getattr(el, "Name", "") or "", candidates, text_col)
        if not match:
            continue

        ident = (match.get(ident_col) or "").strip()
        name = (match.get(text_col) or "").strip()
        unit = (match.get(unit_col) or "").strip()

        qty = get_quantity_for_unit(el, unit)  # derive quantity from model by unit
        if qty is None:
            continue

        try:
            unit_cost = parse_decimal_eu(match.get(unit_cost_col, ""))
        except Exception:
            continue

        matched += 1
        key = (ident, name, unit, float(unit_cost))
        if key not in agg:
            agg[key] = {
                "ident": ident,
                "name": name,
                "unit": unit,
                "unit_cost": float(unit_cost),
                "quantity_total": 0.0,
                "elements_count": 0,
            }

        agg[key]["quantity_total"] += float(qty)
        agg[key]["elements_count"] += 1

    # Build final list and grand total
    items: List[Dict[str, object]] = []
    grand_total = 0.0
    for (ident, name, unit, unit_cost), data in agg.items():
        qty = float(data["quantity_total"])
        line_total = qty * float(unit_cost)
        grand_total += line_total
        items.append(
            {
                "ident": ident,
                "name": name,
                "unit": unit,
                "unit_cost": float(unit_cost),
                "quantity_total": qty,
                "elements_count": int(data["elements_count"]),
                "line_total": line_total,
            }
        )

    items.sort(key=lambda x: (x["ident"], x["name"]))
    return {"items": items, "grand_total": grand_total, "scanned": scanned, "matched": matched}


def write_cost_estimation_report(
    ifc_file,
    csv_path: str,
    *,
    output_dir: str = "output",
    filename: str = "cost_estimation.txt",
    ident_col: str = "Identification Code",
    text_col: str = "Name",
    unit_col: str = "Measurement Unit",
    unit_cost_col: str = "IfcCostValue",
    ifc_match_col: str = "Ifc Match",
    delimiter: str = ";",
    encoding: str = "cp1252",
) -> Tuple[str, float]:
    """Write a simple text report; return (path, grand_total)."""
    summary = build_cost_estimation_summary(
        ifc_file,
        csv_path,
        ident_col=ident_col,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        ifc_match_col=ifc_match_col,
        delimiter=delimiter,
        encoding=encoding,
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    items: List[Dict[str, object]] = summary["items"]
    grand_total: float = float(summary["grand_total"])

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("COST ESTIMATION\n")
        f.write("===============\n\n")
        f.write(f"Rows: {len(items)}\n\n")
        f.write("Identification;Name;Unit;Qty;Unit Cost;Line Total;#Elems\n")
        for it in items:
            f.write(
                f"{it['ident']};"
                f"{it['name']};"
                f"{it['unit']};"
                f"{_format_number_eu(it['quantity_total'])};"
                f"{_format_number_eu(it['unit_cost'])};"
                f"{_format_number_eu(it['line_total'])};"
                f"{it['elements_count']}\n"
            )

    return out_path, grand_total