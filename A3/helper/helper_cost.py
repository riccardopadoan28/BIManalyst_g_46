import csv
import os
from collections import defaultdict
import re
from ifcopenshell.guid import new as new_guid
from typing import Dict, List, Tuple

try:
    from ifcopenshell import api as ifc_api
except Exception as e:
    raise ImportError("ifcopenshell.api non disponibile. Installa IfcOpenShell con le API abilitate.") from e

from .helper_read import read_price_list, normalize_text, parse_decimal_eu
from .helper_get import map_elements_to_price_rows_by_type_name


def ensure_cost_schedule(ifc_file, name: str = "Price List", predefined_type: str = "COSTPLAN"):
    for s in ifc_file.by_type("IfcCostSchedule"):
        if (getattr(s, "Name", None) or "") == name:
            return s
    return ifc_api.run("cost.add_cost_schedule", ifc_file, name=name, predefined_type=predefined_type)


def _schedule_children_cost_items(schedule) -> List[object]:
    children: List[object] = []
    for rel in getattr(schedule, "IsNestedBy", []) or []:
        for o in getattr(rel, "RelatedObjects", []) or []:
            if o.is_a("IfcCostItem"):
                children.append(o)
    return children


def _find_item_by_name_or_identification(schedule, name: str, identification: str | None):
    for item in _schedule_children_cost_items(schedule):
        if (getattr(item, "Name", None) or "") == name:
            return item
        if identification and (getattr(item, "Identification", None) or "") == identification:
            return item
    return None


def add_or_get_cost_item(
    ifc_file,
    parent_schedule,
    *,
    name: str,
    identification: str | None = None,
    description: str | None = None,
):
    existing = _find_item_by_name_or_identification(parent_schedule, name, identification)
    if existing:
        return existing

    # Crea il nuovo cost item
    item = ifc_api.run("cost.add_cost_item", ifc_file, cost_schedule=parent_schedule)

    # Imposta gli attributi direttamente (compatibile con versioni senza attribute.edit)
    if name:
        item.Name = name
    if identification:
        item.Identification = identification
    if description:
        item.Description = description

    return item



def add_unit_cost_value(ifc_file, item, *, amount=None, currency=None, cost_type=None):
    # Crea la relazione IfcCostValue correttamente
    cost_value = ifc_api.run("cost.add_cost_value", ifc_file, parent=item)

    # L’attributo AppliedValue deve essere un’entità IFC, non un float!
    if amount is not None:
        cost_value.AppliedValue = ifc_file.create_entity("IfcMonetaryMeasure", amount)

    # Currency non è un campo diretto: serve una relazione monetaria opzionale
    if currency:
        try:
            # Se la tua build supporta il tipo IfcContextDependentUnit o IfcCurrencyRelationship
            cost_value.Currency = currency  # alcune build accettano stringhe per semplicità
        except Exception:
            pass  # se non supportato, semplicemente ignora

    if cost_type:
        cost_value.Category = cost_type  # UNIT, TOTAL, MATERIAL, ecc.

    return cost_value


def import_price_list_as_cost_schedule_from_csv(
    ifc_file,
    csv_path: str,
    *,
    schedule_name: str = "Price List",
    text_col: str = "Text",
    number_col: str = "Number",
    position_col: str = "Position",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    currency: str = "EUR",
    delimiter: str = ";",
    encoding: str = "cp1252",
) -> Tuple[object, Dict[str, object]]:

    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)
    schedule = ensure_cost_schedule(ifc_file, schedule_name)

    text_to_item: Dict[str, object] = {}

    for r in rows:
        text = (r.get(text_col) or "").strip()
        if not text:
            continue

        uc_raw = r.get(unit_cost_col)
        if not uc_raw:
            continue

        try:
            unit_cost = parse_decimal_eu(uc_raw)
        except Exception:
            continue

        identification = None
        pos = (r.get(position_col) or "").strip()
        num = (r.get(number_col) or "").strip()
        if pos or num:
            identification = f"{pos} {num}".strip()

        description = None
        unit = (r.get(unit_col) or "").strip()
        if unit:
            description = f"Unit: {unit}"

        item = add_or_get_cost_item(
            ifc_file,
            schedule,
            name=text,
            identification=identification,
            description=description,
        )
        add_unit_cost_value(ifc_file, item, amount=unit_cost, currency=currency, cost_type="UNIT")

        text_to_item[normalize_text(text)] = item

    return schedule, text_to_item


def assign_elements_to_cost_items_by_type_name_from_csv(
    ifc_file,
    csv_path: str,
    *,
    schedule_name: str = "Price List",
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    delimiter: str = ";",
    encoding: str = "cp1252",
    filter_ifc_classes: Tuple[str, ...] = ("IfcBeam", "IfcColumn", "IfcMember", "IfcSlab", "IfcWall", "IfcWallStandardCase"),
) -> Dict[str, int]:

    schedule, text_to_item = import_price_list_as_cost_schedule_from_csv(
        ifc_file,
        csv_path,
        schedule_name=schedule_name,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        delimiter=delimiter,
        encoding=encoding,
    )

    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)
    matches = map_elements_to_price_rows_by_type_name(
        ifc_file,
        rows,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        filter_ifc_classes=filter_ifc_classes,
    )

    assigned = 0
    skipped = 0
    for m in matches:
        el = m["element"]
        key = normalize_text(m["row"].get(text_col, ""))
        item = text_to_item.get(key)
        if not item:
            skipped += 1
            continue

        # evita doppie assegnazioni
        already = False
        for rel in getattr(el, "HasAssignments", []) or []:
            if rel.is_a("IfcRelAssignsToControl") and rel.RelatingControl == item:
                already = True
                break
        if already:
            continue

        ifc_api.run("cost.assign_products", ifc_file, products=[el], cost_item=item)
        assigned += 1

    return {"assigned": assigned, "skipped": skipped}


def build_cost_report_preview_from_csv(
    ifc_file,
    csv_path: str,
    *,
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    delimiter: str = ";",
    encoding: str = "cp1252",
    filter_ifc_classes: Tuple[str, ...] = ("IfcBeam", "IfcColumn", "IfcMember", "IfcSlab", "IfcWall", "IfcWallStandardCase"),
) -> List[Dict[str, object]]:
    rows = read_price_list(csv_path, delimiter=delimiter, encoding=encoding)
    return map_elements_to_price_rows_by_type_name(
        ifc_file,
        rows,
        text_col=text_col,
        unit_col=unit_col,
        unit_cost_col=unit_cost_col,
        filter_ifc_classes=filter_ifc_classes,
    )

