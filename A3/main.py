"""
Main pipeline:
- Copy input IFC to a writable copy
- Open and inspect elements (optional)
- Import CSV price list, create/attach cost data, assign elements
- Write IFC and a simple cost report + BOQ total
"""

import os
import re
import shutil
import ifcopenshell as ifc

from helper.helper_get import (
    get_all_struct_elements,
    get_rectangle_profiles_from_columns,
    get_non_rectangle_profiles_from_columns,
)
from helper.helper_cost import assign_elements_to_cost_items_by_type_name_from_csv
from helper.helper_write import write_cost_estimation_report


def _extract_total_cost_from_summary(summary_path: str):
    """Extract last numeric value from the line containing 'total' (case-insensitive)."""
    if not os.path.exists(summary_path):
        return None
    total = None
    with open(summary_path, "r", encoding="utf-8") as f:
        for line in f:
            if "total" in line.lower():
                nums = re.findall(r"[-+]?\d[\d\s\.,]*", line)
                if not nums:
                    continue
                s = nums[-1].replace(" ", "")
                # handle 1.234,56 or 1,234.56
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(",", ".")
                try:
                    total = float(s)
                except Exception:
                    pass
    return total


def main():
    # Paths
    in_ifc_path = r"C:\Users\ricki\Desktop\GitHub\BIManalyst_g_46\A3\input\25-08-D-STR.ifc"
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Working IFC copy
    out_ifc_path = os.path.join(output_dir, "25-08-D-STR_cost.ifc")
    if os.path.exists(out_ifc_path):
        os.remove(out_ifc_path)
    shutil.copy2(in_ifc_path, out_ifc_path)

    # Open model for edits
    model = ifc.open(out_ifc_path)

    # Optional: quick element listings
    get_all_struct_elements(model, output_dir=output_dir, filename="elements.txt")
    get_rectangle_profiles_from_columns(model)
    get_non_rectangle_profiles_from_columns(model)

    # CSV price list -> create items/values + assign products
    price_csv = os.path.join(os.path.dirname(__file__), "input", "price_list_new.csv")
    res = assign_elements_to_cost_items_by_type_name_from_csv(
        model,
        price_csv,
        schedule_name="Price List",
        # If headers differ, pass ident_col=..., text_col=..., ifc_match_col=..., unit_cost_col=...
    )
    print(f"Assegnazioni: {res}")

    # Save IFC
    model.write(out_ifc_path)

    # Write text report
    summary_path, _ = write_cost_estimation_report(
        model,
        price_csv,
        output_dir=output_dir,
        filename="cost_estimation.txt",
    )

    # Write BOQ total
    total_cost = _extract_total_cost_from_summary(summary_path)
    boq_text_path = os.path.join(output_dir, "BOQ.text")
    with open(boq_text_path, "w", encoding="utf-8") as f:
        f.write(
            f"Total IfcCostItem: {total_cost:.2f} €\n"
            if total_cost is not None
            else "Total IfcCostItem: NON TROVATO\n"
        )
    print(f"Totale IfcCostItem scritto in: {boq_text_path}")
    print(f"IFC copia modificata salvata in: {out_ifc_path}")


if __name__ == "__main__":
    main()