"""
Cost helpers:
- Ensure/return IfcCostSchedule
- Create/find IfcCostItem and add IfcCostValue
- Import price list from CSV
- Assign products to cost items (IfcRelAssignsToControl)
"""

import csv
import os
import re
import difflib
from collections import defaultdict
from typing import Dict, List, Tuple
from ifcopenshell.guid import new as new_guid

try:
    from ifcopenshell import api as ifc_api
except Exception as e:
    raise ImportError("ifcopenshell.api not available. Install IfcOpenShell with API support.") from e

from .helper_read import read_price_list, normalize_text, parse_decimal_eu

# Find or create IfcCostSchedule by name ensuring only one exists.
def ensure_cost_schedule(model, name: str = "Price List", predefined_type: str = "COSTPLAN"):
    for s in model.by_type("IfcCostSchedule"):
        if (getattr(s, "Name", None) or "") == name:
            return s
    return ifc_api.run("cost.add_cost_schedule", model, name=name, predefined_type=predefined_type)

# Collect direct child IfcCostItem nested under schedule. Searching existing items.
def _schedule_children_cost_items(schedule) -> List[object]:
    children: List[object] = []
    for rel in getattr(schedule, "IsNestedBy", []) or []:
        for o in getattr(rel, "RelatedObjects", []) or []:
            if o.is_a("IfcCostItem"):
                children.append(o)
    return children

# Find item by Name or Identification among schedule children. Avoid duplicate cost items
def _find_item_by_name_or_identification(schedule, name: str, identification: str | None):
    for item in _schedule_children_cost_items(schedule):
        if (getattr(item, "Name", None) or "") == name:
            return item
        if identification and (getattr(item, "Identification", None) or "") == identification:
            return item
    return None

# Find an IfcCostItem (by name/ident) or create one under the schedule.
def add_or_get_cost_item(model, cost_schedule, name, identification=None, description=None):
    for ci in model.by_type("IfcCostItem"):
        if ci.Name == name and (identification is None or getattr(ci, "Identification", None) == identification):
            return ci
    item = ifc_api.run("cost.add_cost_item", model, cost_schedule=cost_schedule)
    attrs = {"Name": name}
    if identification is not None:
        attrs["Identification"] = identification
    if description is not None:
        attrs["Description"] = description
    if attrs:
        ifc_api.run("cost.edit_cost_item", model, cost_item=item, attributes=attrs)
    return item

# Creates an IfcCostValue as a child of a cost item, set AppliedValue and store label in Name
def add_unit_cost_value(model, item, amount, cost_type="UNIT"):
    cost_value = ifc_api.run("cost.add_cost_value", model, parent=item)
    ifc_api.run(
        "cost.edit_cost_value",
        model,
        cost_value=cost_value,
        attributes={"AppliedValue": float(amount), "Name": str(cost_type)},
    )
    return cost_value

# Fuzzy match element name to the best CSV row on the given column.
def _best_match(element_name: str, candidates: List[Dict[str, str]], name_col: str) -> Dict[str, str] | None:
    if not candidates:
        return None
    base = (element_name or "").strip().lower()
    scores = [(difflib.SequenceMatcher(None, base, (c.get(name_col) or "").strip().lower()).ratio(), c) for c in candidates]
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[0][1] if scores else None

# Create schedule and one IfcCostItem (+ unit cost) per CSV row; return (schedule, code->item). importing price lists directly into IFC
def import_price_list_as_cost_schedule_from_csv(
    model,
    csv_path: str,
    *,
    schedule_name: str = "Price List 2025",
    ident_col: str = "Identification Code",
    text_col: str = "Name",
    unit_cost_col: str = "IfcCostValue",
    delimiter: str = ";",
    encoding: str = "cp1252",
) -> Tuple[object, Dict[str, object]]:

    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)
    schedule = ensure_cost_schedule(model, schedule_name)

    code_to_item: Dict[str, object] = {}
    for r in rows:
        code = (r.get(ident_col) or "").strip()
        name = (r.get(text_col) or "").strip()
        if not code or not name or code in code_to_item:
            continue

        uc_raw = r.get(unit_cost_col)
        try:
            unit_cost = parse_decimal_eu(uc_raw) if uc_raw is not None else None
        except Exception:
            unit_cost = None

        item = add_or_get_cost_item(model, schedule, name=name, identification=code)
        if unit_cost is not None:
            add_unit_cost_value(model, item, amount=unit_cost, cost_type="UNIT")
        code_to_item[code] = item

    return schedule, code_to_item


def assign_elements_to_cost_items_by_type_name_from_csv(
    model,
    csv_path: str,
    *,
    schedule_name: str = "Price List 2025",
    ident_col: str = "Identification Code",
    text_col: str = "Name",
    ifc_match_col: str = "Ifc Match",
    unit_cost_col: str = "IfcCostValue",
    delimiter: str = ";",
    encoding: str = "cp1252",
    filter_ifc_classes: Tuple[str, ...] = (),  # currently scans all IfcElement
) -> Dict[str, int]:
    """
    For each IfcElement:
    - filter CSV by Ifc Match == element.is_a()
    - fuzzy match by Name
    - create/reuse IfcCostItem (by Identification Code), add unit cost, relate element
    """
    schedule = ensure_cost_schedule(model, schedule_name)
    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)

    # Index rows by IFC class
    by_class: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        cls = (r.get(ifc_match_col) or "").strip() or "IfcElement"
        by_class.setdefault(cls, []).append(r)

    code_to_item: Dict[str, object] = {}
    assigned = 0
    skipped_no_candidates = 0
    skipped_no_match = 0

    for e in model.by_type("IfcElement"):
        candidates = by_class.get(e.is_a(), [])
        if not candidates:
            skipped_no_candidates += 1
            continue

        match = _best_match(getattr(e, "Name", "") or "", candidates, text_col)
        if not match:
            skipped_no_match += 1
            continue

        code = (match.get(ident_col) or "").strip()
        if not code:
            skipped_no_match += 1
            continue

        # Reuse/create item once per code
        item = code_to_item.get(code)
        if not item:
            item = add_or_get_cost_item(
                model,
                schedule,
                name=(match.get(text_col) or "").strip() or code,
                identification=code,
            )
            uc_raw = match.get(unit_cost_col)
            try:
                unit_cost = parse_decimal_eu(uc_raw) if uc_raw is not None else None
            except Exception:
                unit_cost = None
            if unit_cost is not None:
                add_unit_cost_value(model, item, amount=unit_cost, cost_type="UNIT")
            code_to_item[code] = item

        # Skip if already assigned to this control
        already = False
        for rel in getattr(e, "HasAssignments", []) or []:
            if rel.is_a("IfcRelAssignsToControl") and rel.RelatingControl == item:
                already = True
                break
        if already:
            continue

        # Assign single related_object (API expects one)
        try:
            ifc_api.run(
                "control.assign_control",
                model,
                relating_control=item,
                related_object=e,
            )
            assigned += 1  # count successful links
        except ModuleNotFoundError:
            model.create_entity(
                "IfcRelAssignsToControl",
                GlobalId=new_guid(),
                RelatedObjects=[e],
                RelatingControl=item,
            )
            assigned += 1

    return {"assigned": assigned, "skipped_no_candidates": skipped_no_candidates, "skipped_no_match": skipped_no_match}

