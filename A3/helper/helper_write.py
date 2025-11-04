import ifcopenshell as ifc
import os
from typing import Dict, List, Tuple

from .helper_read import read_price_list
from .helper_get import map_elements_to_price_rows_by_type_name


def _format_number_eu(value: float, decimals: int = 2) -> str:
    s = f"{value:,.{decimals}f}"  # 1,234,567.89
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def build_cost_estimation_summary(
    ifc_file,
    csv_path: str,
    *,
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    position_col: str = "Position",
    number_col: str = "Number",
    structural_type_col: str = "Structural Element Type",
    delimiter: str = ";",
    encoding: str = "cp1252",
    filter_ifc_classes: Tuple[str, ...] = (
        "IfcBeam", "IfcColumn", "IfcMember", "IfcSlab", "IfcWall", "IfcWallStandardCase"
    ),
) -> Dict[str, object]:
    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)
    matches = map_elements_to_price_rows_by_type_name(
        ifc_file,
        rows,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        filter_ifc_classes=filter_ifc_classes,
    )

    # Aggregazione per riga di listino
    agg: Dict[Tuple[str, str, float, str, str], Dict[str, object]] = {}
    # Breakdown
    by_struct_type: Dict[str, Dict[str, object]] = {}
    by_ifc_class: Dict[str, Dict[str, object]] = {}

    for m in matches:
        r = m["row"]
        text = (r.get(text_col) or "").strip()
        unit = (r.get(unit_col) or "").strip()
        position = (r.get(position_col) or "").strip()
        number = (r.get(number_col) or "").strip()
        struct_type = (r.get(structural_type_col) or "").strip()
        unit_cost = float(m["unit_cost"])
        qty = float(m["quantity"])
        line_total = qty * unit_cost
        ifc_class = m["element"].is_a()

        key = (text, unit, unit_cost, position, number)
        if key not in agg:
            agg[key] = {
                "position": position,
                "number": number,
                "text": text,
                "unit": unit,
                "unit_cost": unit_cost,
                "quantity_total": 0.0,
                "elements_count": 0,
            }
        agg[key]["quantity_total"] = float(agg[key]["quantity_total"]) + qty
        agg[key]["elements_count"] = int(agg[key]["elements_count"]) + 1

        if struct_type not in by_struct_type:
            by_struct_type[struct_type] = {"line_total": 0.0, "quantity_total": 0.0, "elements_count": 0}
        by_struct_type[struct_type]["line_total"] += line_total
        by_struct_type[struct_type]["quantity_total"] += qty
        by_struct_type[struct_type]["elements_count"] += 1

        if ifc_class not in by_ifc_class:
            by_ifc_class[ifc_class] = {"line_total": 0.0, "quantity_total": 0.0, "elements_count": 0}
        by_ifc_class[ifc_class]["line_total"] += line_total
        by_ifc_class[ifc_class]["quantity_total"] += qty
        by_ifc_class[ifc_class]["elements_count"] += 1

    items: List[Dict[str, object]] = []
    grand_total = 0.0
    for (text, unit, unit_cost, position, number), data in agg.items():
        qty = float(data["quantity_total"])
        line_total = qty * float(unit_cost)
        grand_total += line_total
        items.append({
            "position": position,
            "number": number,
            "text": text,
            "unit": unit,
            "unit_cost": float(unit_cost),
            "quantity_total": qty,
            "elements_count": int(data["elements_count"]),
            "line_total": line_total,
        })

    items.sort(key=lambda x: (x["position"], x["number"], x["text"]))
    by_struct_type_sorted = sorted(by_struct_type.items(), key=lambda kv: kv[1]["line_total"], reverse=True)
    by_ifc_class_sorted = sorted(by_ifc_class.items(), key=lambda kv: kv[1]["line_total"], reverse=True)

    return {
        "items": items,
        "grand_total": grand_total,
        "by_struct_type": by_struct_type_sorted,
        "by_ifc_class": by_ifc_class_sorted,
    }


def write_cost_estimation_report(
    ifc_file,
    csv_path: str,
    *,
    output_dir: str = "output",
    filename: str = "cost_estimation.txt",
    currency: str = "EUR",
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    position_col: str = "Position",
    number_col: str = "Number",
    structural_type_col: str = "Structural Element Type",
    delimiter: str = ";",
    encoding: str = "cp1252",
    filter_ifc_classes: Tuple[str, ...] = (
        "IfcBeam", "IfcColumn", "IfcMember", "IfcSlab", "IfcWall", "IfcWallStandardCase"
    ),
) -> str:
    summary = build_cost_estimation_summary(
        ifc_file,
        csv_path,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        position_col=position_col,
        number_col=number_col,
        structural_type_col=structural_type_col,
        delimiter=delimiter,
        encoding=encoding,
        filter_ifc_classes=filter_ifc_classes,
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    items: List[Dict[str, object]] = summary["items"]
    grand_total: float = float(summary["grand_total"])
    by_struct_type = summary["by_struct_type"]
    by_ifc_class = summary["by_ifc_class"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("COST ESTIMATION\n")
        f.write("===============\n\n")
        f.write(f"Currency: {currency}\n")
        f.write(f"Rows: {len(items)}\n\n")

        # Dettaglio righe aggregate
        f.write("Position;Number;Text;Unit;Qty;Unit Cost;Line Total;#Elems\n")
        for it in items:
            f.write(
                f"{it['position']};"
                f"{it['number']};"
                f"{it['text']};"
                f"{it['unit']};"
                f"{_format_number_eu(it['quantity_total'])};"
                f"{_format_number_eu(it['unit_cost'])};"
                f"{_format_number_eu(it['line_total'])};"
                f"{it['elements_count']}\n"
            )

        f.write("\nBREAKDOWN BY STRUCTURAL ELEMENT TYPE\n")
        f.write("Type;Qty Total;Line Total;#Elems\n")
        for t, data in by_struct_type:
            f.write(
                f"{t};"
                f"{_format_number_eu(float(data['quantity_total']))};"
                f"{_format_number_eu(float(data['line_total']))};"
                f"{int(data['elements_count'])}\n"
            )

        f.write("\nBREAKDOWN BY IFC CLASS\n")
        f.write("IfcClass;Qty Total;Line Total;#Elems\n")
        for cls, data in by_ifc_class:
            f.write(
                f"{cls};"
                f"{_format_number_eu(float(data['quantity_total']))};"
                f"{_format_number_eu(float(data['line_total']))};"
                f"{int(data['elements_count'])}\n"
            )

        f.write("\n")
        f.write(f"GRAND TOTAL ({currency}): {_format_number_eu(grand_total)}\n")

    return out_path