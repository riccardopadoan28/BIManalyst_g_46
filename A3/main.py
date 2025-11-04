# Importations
import ifcopenshell as ifc
import os
import re

from helper.helper_get import (
    get_all_struct_elements,
    get_rectangle_profiles_from_columns,
    get_non_rectangle_profiles_from_columns,
)
from helper.helper_cost import (
    assign_elements_to_cost_items_by_type_name_from_csv,
)
from helper.helper_write import (
    write_cost_estimation_report,
)


def _extract_total_cost_from_summary(summary_path: str):
    if not os.path.exists(summary_path):
        return None
    total = None
    with open(summary_path, "r", encoding="utf-8") as f:
        for line in f:
            if "total" in line.lower():
                nums = re.findall(r"[-+]?\d[\d\s\.,]*", line)
                if nums:
                    s = nums[-1].replace(" ", "")
                    if "," in s and "." in s:
                        s = s.replace(".", "").replace(",", ".")
                    elif "," in s:
                        s = s.replace(",", ".")
                    try:
                        total = float(s)
                    except:
                        pass
    return total


# Define main
def main():
    # IFC in input
    model = ifc.open(r"C:\Users\ricki\Desktop\GitHub\BIManalyst_g_46\A3\input\25-08-D-STR.ifc")

    # Output dir
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Esporta elenco elementi (se implementato)
    get_all_struct_elements(model, output_dir=output_dir, filename="elements.txt")
    get_rectangle_profiles_from_columns(model)
    get_non_rectangle_profiles_from_columns(model)

    # CSV listino
    price_csv = os.path.join(os.path.dirname(__file__), "input", "price_list_new.csv")

    # Assegna elementi -> CostItem (crea IfcCostSchedule/IfcCostItem/CostValue)
    res = assign_elements_to_cost_items_by_type_name_from_csv(
        model,
        price_csv,
        schedule_name="Price List",
    )
    print(f"Assegnazioni: {res}")

    # Salva IFC con i costi
    out_ifc_path = os.path.join(output_dir, "25-08-D-STR_cost.ifc")
    model.write(out_ifc_path)

    # Scrivi il report cost_estimation.txt e sovrascrivi sempre
    cost_summary = os.path.join(output_dir, "cost_estimation.txt")
    if os.path.exists(cost_summary):
        os.remove(cost_summary)
    write_cost_estimation_report(
        model,
        price_csv,
        output_dir=output_dir,
        filename="cost_estimation.txt",
        currency="EUR",
    )

    # Estrai il totale e scrivi in BOQ.text
    total_cost = _extract_total_cost_from_summary(cost_summary)
    boq_text_path = os.path.join(output_dir, "BOQ.text")
    with open(boq_text_path, "w", encoding="utf-8") as f:
        if total_cost is not None:
            f.write(f"Total IfcCostItem: {total_cost:.2f} €\n")
        else:
            f.write("Total IfcCostItem: NON TROVATO\n")

    print(f"Totale IfcCostItem scritto in: {boq_text_path}")
    print(f"IFC con costi salvato in: {out_ifc_path}")


if __name__ == "__main__":
    main()