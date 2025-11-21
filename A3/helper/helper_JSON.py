"""
Creates a JSON file that reflects the BOQ_total.txt structure.
Aggregates data from IfcCostItem without level breakdown.
"""
import json
import os
from datetime import datetime
from collections import defaultdict

from .helper_read import read_price_list
from .helper_get import get_quantity_for_unit

def output_to_json(model, csv_path=None, output_dir="output"):

    os.makedirs(output_dir, exist_ok=True)
    
    # Define output path
    out_path = os.path.join(output_dir, "A3_TOOL.json")

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

    # Map cost item -> elements
    item_map = defaultdict(list)
    for rel in model.by_type("IfcRelAssignsToControl"):
        ci = getattr(rel, "RelatingControl", None)
        if not ci or not ci.is_a("IfcCostItem"):
            continue
        for obj in rel.RelatedObjects or []:
            if obj and obj.is_a("IfcElement"):
                item_map[ci.id()].append(obj)

    items = []
    grand_total = 0.0

    # Process each cost item
    for cid, elems in sorted(item_map.items(), key=lambda x: x[0]):
        ci = model[cid]
        ident = getattr(ci, "Identification", "") or ci.GlobalId
        descr = getattr(ci, "Name", "") or "(no name)"
        
        # Extract measurement unit
        if ident in csv_unit_map:
            unit = csv_unit_map[ident]
        else:
            vals = getattr(ci, "CostValues", None) or []
            if vals:
                u = getattr(vals[0], "Unit", None)
                unit = getattr(u, "Name", "") if u else "-"
            else:
                unit = "-"
        
        # Extract unit cost
        vals = getattr(ci, "CostValues", None) or []
        if vals:
            v = vals[0].AppliedValue
            try:
                rate = float(getattr(v, "wrappedValue", v))
            except Exception:
                s = str(v)
                if "(" in s and ")" in s:
                    try:
                        rate = float(s.split("(")[1].split(")")[0])
                    except Exception:
                        rate = 0.0
                else:
                    rate = 0.0
        else:
            rate = 0.0

        # Sum quantities of all elements
        qty_sum = 0.0
        for e in elems:
            q = get_quantity_for_unit(e, unit, model=model)
            if q is None:
                q = 1.0
            qty_sum += float(q)
        
        amount = rate * qty_sum
        grand_total += amount
        
        # Add item to JSON
        items.append({
            "itemCode": ident,
            "description": descr,
            "unit": unit,
            "quantity": round(qty_sum, 4),
            "unitCost": round(rate, 2),
            "totalAmount": round(amount, 2)
        })

    # Final JSON structure
    output_data = {
        "document": {
            "title": "BILL OF QUANTITIES (BOQ) – TOTALS ONLY",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "IFC Model Analysis"
        },
        "items": items,
        "summary": {
            "total": round(grand_total, 2),
            "currency": "DKK"
        }
    }

    # Write JSON file
    with open(out_path, "w", encoding="utf-8") as json_file:
        json.dump(output_data, json_file, indent=2, ensure_ascii=False)
    
    print(f"JSON output saved to: {out_path}")
    return out_path