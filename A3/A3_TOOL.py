"""
Main pipeline:
- Ask for IFC path (or take first CLI argument)
- Open IFC (not stored in repo)
- Import CSV price list, create/attach cost data, assign elements
- Write cost report (QTO.txt)
"""

import os
import sys
import re
from pathlib import Path
from xml.parsers.expat import model
import ifcopenshell

from helper.helper_cost import assign_elements_to_cost_items_by_type_name_from_csv
from helper.helper_write import (
    write_qto_types_no_cost,
    write_boq_report,
    write_qto_types_no_cost_totals,
    write_boq_report_totals,
)
from helper.helper_JSON import output_to_json


def structural_cost_estimation(model_path, price_csv_path, output_dir="output"):
    """
    Main pipeline for structural cost estimation.
    - model_path: Path to the IFC model file.
    - price_csv_path: Path to the CSV price list file.
    """
    price_csv = price_csv_path
# Example of using os.path.join
    path = os.path.join("/home", "user", "documents", "/etc", "config.txt")
    print(os.path)

    # Open IFC model (original file is never overwritten; all changes are saved to a new copy)
    model = ifcopenshell.open(str(model_path))
    print(f"Opened IFC: {model_path}")

    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.isfile(price_csv):
        raise FileNotFoundError(f"No file found at {price_csv}!")
    assign_elements_to_cost_items_by_type_name_from_csv(
        model,
        price_csv,
        schedule_name="Price List",
    )

    # Single final text report
    qto_path = write_qto_types_no_cost(model, output_dir=output_dir, filename="QTO.txt")
    boq_path = write_boq_report(model, output_dir=output_dir, filename="BOQ.txt")
    qto_tot_path = write_qto_types_no_cost_totals(model, output_dir=output_dir, filename="QTO_total.txt")
    boq_tot_path = write_boq_report_totals(model, output_dir=output_dir, filename="BOQ_total.txt")
    print(f"Written QTO: {os.path.abspath(qto_path)}")
    print(f"Written BOQ: {os.path.abspath(boq_path)}")
    print(f"Written QTO (totals): {os.path.abspath(qto_tot_path)}")
    print(f"Written BOQ (totals): {os.path.abspath(boq_tot_path)}")

    # Generate output IFC filename based on input model_path
    input_stem = model_path.stem
    input_ext = model_path.suffix
    output_ifc_name = f"{input_stem}_cost{input_ext}"
    output_ifc_path = os.path.join(output_dir, output_ifc_name)
    model.write(output_ifc_path)
    print(f"Updated IFC written to: {os.path.abspath(output_ifc_path)}")

    # Generate JSON output
    json_path = output_to_json(model)


if __name__ == "__main__":
    # Determine IFC path: CLI arg else prompt
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = input("Enter absolute path to IFC model: ").strip()

    model_path = Path(input_path)
    if not model_path.is_file():
        raise FileNotFoundError(f"No file found at {model_path}!")
    # Assign cost items from price list
    price_csv = input("Enter price list path:").strip()

    structural_cost_estimation(model_path, price_csv)




# def do_stuff(model_path, price_csv_path, output_dir="output"):
#     load model
#     load price_csv_path
#     do calculations

#     return jsonstring

