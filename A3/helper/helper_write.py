"""
Reporting helpers:
- Build a summarized cost estimation (grouping rows)
- Write a simple CSV-like text report

Functions:
- _format_number_eu: Format numbers with EU style (1.234,56)
- _best_match: Fuzzy pick the best CSV row for an element by comparing names
- build_cost_estimation_summary: Aggregate quantities and costs by (ident, name, unit, unit_cost)
- write_cost_estimation_report: Write a simple text report; return (path, grand_total)
- _fmt_table: Format data as aligned text table with headers and separator lines
- write_qto_types_no_cost: Write QTO report grouped by IfcElementType and Level (no costs)
- write_qto_types_no_cost_totals: Write QTO total-only report (count per type, no level split)
- write_boq_report: Write BOQ report with lines split by Cost Item and Level
- write_boq_report_totals: Write BOQ total-only report (one line per Cost Item, no level split)
- _get_level_name: Return the IfcBuildingStorey name containing the element
"""

import os
import difflib
from typing import Dict, List, Tuple
from collections import defaultdict, Counter
import datetime

from .helper_read import read_price_list, parse_decimal_eu
from .helper_get import get_quantity_for_unit

# Format numbers with EU style (1.234,56).
# Converts standard float format to European notation with dot as thousands separator
# and comma as decimal separator.
def _format_number_eu(value: float, decimals: int = 2) -> str:
    """Format 1234.56 as 1.234,56 (EU style)."""
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# Fuzzy pick the best CSV row for an element by comparing names.
# Uses difflib.SequenceMatcher for similarity scoring.
def _best_match(element_name: str, candidates: List[Dict[str, str]], name_col: str) -> Dict[str, str] | None:
    if not candidates:
        return None
    base = (element_name or "").strip().lower()
    scores = [
        (difflib.SequenceMatcher(None, base, (c.get(name_col) or "").strip().lower()).ratio(), c)
        for c in candidates
    ]
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[0][1] if scores else None

# Aggregate quantities and costs by (ident, name, unit, unit_cost).
# Groups multiple elements with same price list item and sums quantities.
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

# Write a simple text report with cost estimation; return (path, grand_total).
# Creates semicolon-separated text file with aggregated cost data.
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

# Format data as aligned text table with headers and separator lines.
# Creates human-readable table with automatic column width calculation.
def _fmt_table(headers, rows, max_col_width=48):
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = min(max(widths[i], len(str(cell))), max_col_width)
    line_sep = "─"
    header_line = " | ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    sep = "─┼─".join(line_sep * widths[i] for i in range(len(headers)))
    out = [header_line, sep]
    for r in rows:
        out.append(" | ".join(f"{str(cell):<{widths[i]}}" for i, cell in enumerate(r)))
    return out

# Write QTO report grouped by IfcElementType and Level (no costs).
# Table shows subtotals per type and grand total.
def write_qto_types_no_cost(model, output_dir="output", filename="QTO.txt"):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    def _get_type(e):
        if getattr(e, "IsTypedBy", None):
            for rel in e.IsTypedBy:
                if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                    return rel.RelatingType
        for rel in getattr(e, "IsDefinedBy", []) or []:
            if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                return rel.RelatingType
        return None

    # Aggregation structures
    type_level_counts = defaultdict(lambda: defaultdict(int))
    untyped_level_counts = defaultdict(lambda: defaultdict(int))

    total = 0
    for e in model.by_type("IfcElement"):
        total += 1
        level = _get_level_name(e)
        tobj = _get_type(e)
        if tobj:
            tclass = tobj.is_a()
            tname = getattr(tobj, "Name", None) or "(unnamed type)"
            type_level_counts[(tclass, tname)][level] += 1
        else:
            untyped_level_counts[e.is_a()][level] += 1

    # Build table rows
    rows = []
    index = 1
    for (tclass, tname) in sorted(type_level_counts.keys(), key=lambda k: (k[0], k[1])):
        level_map = type_level_counts[(tclass, tname)]
        ttotal = sum(level_map.values())
        for lvl, c in sorted(level_map.items(), key=lambda x: (x[0] or "",)):
            rows.append([index, tclass, tname, lvl, c])
        rows.append(["", "", "Subtotal", f"{tclass}/{tname}", ttotal])
        index += 1

    if untyped_level_counts:
        for base in sorted(untyped_level_counts.keys()):
            level_map = untyped_level_counts[base]
            btotal = sum(level_map.values())
            for lvl, c in sorted(level_map.items(), key=lambda x: (x[0] or "",)):
                rows.append(["", base, "(untyped)", lvl, c])
            rows.append(["", "", "Subtotal", base, btotal])

    headers = ["#", "IfcTypeClass", "Type Name", "Level", "Count"]
    table_lines = _fmt_table(headers, rows)

    today = datetime.date.today().isoformat()
    lines = []
    lines.append("Quantity Take Off (QTO)")
    lines.append(f"Date: {today}")
    lines.append(f"Total Elements: {total}")
    lines.append("")
    lines.extend(table_lines)
    lines.append("")
    lines.append(f"TOTAL COUNT = {total}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path

# Write QTO total-only report (count per type, no level split).
# Provides aggregate counts per IfcTypeObject without level breakdown.
def write_qto_types_no_cost_totals(model, output_dir="output", filename="QTO_total.txt"):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    def _get_type(e):
        if getattr(e, "IsTypedBy", None):
            for rel in e.IsTypedBy:
                if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                    return rel.RelatingType
        for rel in getattr(e, "IsDefinedBy", []) or []:
            if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                return rel.RelatingType
        return None

    counts = Counter()
    untyped = Counter()
    total = 0

    for e in model.by_type("IfcElement"):
        total += 1
        tobj = _get_type(e)
        if tobj:
            tclass = tobj.is_a()
            tname = getattr(tobj, "Name", None) or "(unnamed type)"
            counts[(tclass, tname)] += 1
        else:
            untyped[e.is_a()] += 1

    rows = []
    idx = 1
    for (tclass, tname), c in sorted(counts.items(), key=lambda x: (x[0][0], x[0][1])):
        rows.append([idx, tclass, tname, c])
        idx += 1
    for base, c in sorted(untyped.items(), key=lambda x: (x[0],)):
        rows.append(["", base, "(untyped)", c])

    headers = ["#", "IfcTypeClass", "Type Name", "Count"]
    table_lines = _fmt_table(headers, rows)

    today = datetime.date.today().isoformat()
    lines = []
    lines.append("QUANTITY TAKE OFF (QTO) – TOTALS ONLY")
    lines.append(f"Date: {today}")
    lines.append(f"Total Elements: {total}")
    lines.append("")
    lines.extend(table_lines)
    lines.append("")
    lines.append(f"TOTAL COUNT = {total}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path

# Write BOQ report with lines split by Cost Item and Level.
# Provides per-item total and grand total with level breakdown.
# Columns: Item, Description, Unit, Level, Qty, Rate, Amount.
def write_boq_report(model, output_dir="output", filename="BOQ.txt", csv_path=None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    # CSV units
    csv_unit_map = {}
    if csv_path and os.path.isfile(csv_path):
        try:
            from .helper_read import read_price_list
            rows_csv = read_price_list(csv_path, delimiter=";", encoding="cp1252")
            for r in rows_csv:
                ident = r.get("Identification Code") or r.get("Identification") or ""
                unit = r.get("Unit") or r.get("Measurement Unit") or ""
                if ident:
                    csv_unit_map[ident] = unit
        except Exception:
            pass

    # Assignments
    item_map = defaultdict(list)
    for rel in model.by_type("IfcRelAssignsToControl"):
        ci = getattr(rel, "RelatingControl", None)
        if not ci or not ci.is_a("IfcCostItem"):
            continue
        for obj in rel.RelatedObjects or []:
            if obj and obj.is_a("IfcElement"):
                item_map[ci.id()].append(obj)

    def _unit_cost(ci):
        vals = getattr(ci, "CostValues", None) or []
        if not vals:
            return 0.0
        v = vals[0].AppliedValue
        try:
            return float(getattr(v, "wrappedValue", v))
        except Exception:
            s = str(v)
            if "(" in s and ")" in s:
                try:
                    return float(s.split("(")[1].split(")")[0])
                except Exception:
                    return 0.0
        return 0.0

    def _unit(ci):
        ident = getattr(ci, "Identification", "") or ""
        if ident in csv_unit_map:
            return csv_unit_map[ident]
        vals = getattr(ci, "CostValues", None) or []
        if vals:
            u = getattr(vals[0], "Unit", None)
            return getattr(u, "Name", "") if u else "-"
        return "-"

    from helper.helper_get import get_quantity_for_unit

    rows = []
    grand_total = 0.0

    for cid, elems in sorted(item_map.items(), key=lambda x: x[0]):
        ci = model[cid]
        ident = getattr(ci, "Identification", "") or ci.GlobalId
        descr = getattr(ci, "Name", "") or "(no name)"
        unit = _unit(ci) or "-"
        rate = _unit_cost(ci)

        # Level aggregation
        level_qty = defaultdict(float)
        for e in elems:
            lvl = _get_level_name(e)
            q = get_quantity_for_unit(e, unit, model=model)  # ✅ Aggiungi model=model
            if q is None:
                q = 1.0
            level_qty[lvl] += float(q)

        item_total = 0.0
        for lvl, qty in sorted(level_qty.items(), key=lambda x: (x[0] or "",)):
            amount = rate * qty
            item_total += amount
            rows.append([ident, descr, unit, lvl, 
                        f"{qty:.4f}".replace('.', ','),  # ✅ Virgola per qty
                        f"{rate:.2f}".replace('.', ','),  # ✅ Virgola per rate
                        f"{amount:.2f}".replace('.', ',')])  # ✅ Virgola per amount
        grand_total += item_total
        # Item subtotal line
        rows.append(["", "Item Subtotal", "", "", "", "", f"{item_total:.2f}"])

    headers = ["Item", "Description", "Unit", "Level", "Quantity", "Unit Cost", "Total Amount"]
    table_lines = _fmt_table(headers, rows)

    today = datetime.date.today().isoformat()
    lines = []
    lines.append("BILL OF QUANTITIES (BOQ)")
    lines.append(f"Date: {today}")
    lines.append("")
    lines.extend(table_lines)
    lines.append("")
    lines.append(f"TOTAL: {grand_total:.2f}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path

# Write BOQ total-only report (one line per Cost Item, no level split).
# Provides single aggregate line per cost item with total quantity and amount.
def write_boq_report_totals(model, output_dir="output", filename="BOQ_total.txt", csv_path=None):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    # CSV units map
    csv_unit_map = {}
    if csv_path and os.path.isfile(csv_path):
        try:
            from .helper_read import read_price_list
            rows_csv = read_price_list(csv_path, delimiter=";", encoding="cp1252")
            for r in rows_csv:
                ident = r.get("Identification Code") or r.get("Identification") or ""
                unit = r.get("Unit") or r.get("Measurement Unit") or ""
                if ident:
                    csv_unit_map[ident] = unit
        except Exception:
            pass

    # Assignments: cost item -> elements
    item_map = defaultdict(list)
    for rel in model.by_type("IfcRelAssignsToControl"):
        ci = getattr(rel, "RelatingControl", None)
        if not ci or not ci.is_a("IfcCostItem"):
            continue
        for obj in rel.RelatedObjects or []:
            if obj and obj.is_a("IfcElement"):
                item_map[ci.id()].append(obj)

    def _unit_cost(ci):
        vals = getattr(ci, "CostValues", None) or []
        if not vals:
            return 0.0
        v = vals[0].AppliedValue
        try:
            return float(getattr(v, "wrappedValue", v))
        except Exception:
            s = str(v)
            if "(" in s and ")" in s:
                try:
                    return float(s.split("(")[1].split(")")[0])
                except Exception:
                    return 0.0
        return 0.0

    def _unit(ci):
        ident = getattr(ci, "Identification", "") or ""
        if ident in csv_unit_map:
            return csv_unit_map[ident]
        vals = getattr(ci, "CostValues", None) or []
        if vals:
            u = getattr(vals[0], "Unit", None)
            return getattr(u, "Name", "") if u else "-"
        return "-"

    from helper.helper_get import get_quantity_for_unit

    rows = []
    grand_total = 0.0

    for cid, elems in sorted(item_map.items(), key=lambda x: x[0]):
        ci = model[cid]
        ident = getattr(ci, "Identification", "") or ci.GlobalId
        descr = getattr(ci, "Name", "") or "(no name)"
        unit = _unit(ci) or "-"
        rate = _unit_cost(ci)

        qty_sum = 0.0
        for e in elems:
            q = get_quantity_for_unit(e, unit, model=model)  # ✅ Aggiungi model=model
            if q is None:
                q = 1.0
            qty_sum += float(q)
        amount = rate * qty_sum
        grand_total += amount
        rows.append([ident, descr, unit, f"{qty_sum:.4f}", f"{rate:.2f}", f"{amount:.2f}"])

    headers = ["Item", "Description", "Unit", "Quantity", "Unit Cost", "Total Amount"]
    table_lines = _fmt_table(headers, rows)

    today = datetime.date.today().isoformat()
    lines = []
    lines.append("BILL OF QUANTITIES (BOQ) – TOTALS ONLY")
    lines.append(f"Date: {today}")
    lines.append("")
    lines.extend(table_lines)
    lines.append("")
    lines.append(f"TOTAL: {grand_total:.2f}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path

# Return the IfcBuildingStorey name containing the element, else '(no level)'.
# Traverses spatial containment hierarchy to find building storey.
def _get_level_name(e) -> str:
    try:
        import ifcopenshell.util.element as uel
        container = uel.get_container(e)
        cur = container
        while cur:
            if cur.is_a("IfcBuildingStorey"):
                name = getattr(cur, "Name", None)
                return name if name else cur.GlobalId
            rels = getattr(cur, "Decomposes", []) or []
            cur = rels[0].RelatingObject if rels else None
    except Exception:
        pass
    # Fallback: direct spatial containment
    for rel in getattr(e, "ContainedInStructure", []) or []:
        cur = getattr(rel, "RelatingStructure", None)
        while cur:
            if cur.is_a("IfcBuildingStorey"):
                name = getattr(cur, "Name", None)
                return name if name else cur.GlobalId
            rels = getattr(cur, "Decomposes", []) or []
            cur = rels[0].RelatingObject if rels else None
    return "(no level)"