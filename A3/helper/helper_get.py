"""
Model getters/quantity helpers:
- List element types present in model
- Access base quantities and derive quantities by unit
"""
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import os
import ifcopenshell as ifc
import ifcopenshell.api

from .helper_read import build_price_index_by_text, normalize_text, parse_decimal_eu

# Writes: for each IfcElement (e.g. IfcBeam), the related Ifc...Type (e.g. IfcBeamType),
# number of instances linked to each Type, number of elements without Type, and totals.
# Returns the list (type_name, count, None) for compatibility.
def get_all_struct_elements(
    model,
    output_dir="output",
    filename="QTO.txt",
    *,
    sort: str = "count",
    include_percent: bool = False
):

    # Counts for base class (IfcBeam, IfcColumn, ...)
    base_counts = defaultdict(int)

    # Details for base class
    # base_details[base] = {
    #   "type_class": "IfcBeamType",
    #   "type_name_counts": Counter({ "TypeName": n, ... }),
    #   "untyped": n
    # }
    base_details = {}

    elements = list(model.by_type("IfcElement"))

    for e in elements:
        base = e.is_a()
        base_counts[base] += 1

        # Find RelatingType (IfcRelDefinesByType or IsTypedBy)
        rt = None
        # Prefer IsTypedBy if available
        if getattr(e, "IsTypedBy", None):
            for rel in e.IsTypedBy:
                if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                    rt = rel.RelatingType
                    break
        if rt is None:
            for rel in getattr(e, "IsDefinedBy", []) or []:
                if rel and rel.is_a("IfcRelDefinesByType") and rel.RelatingType:
                    rt = rel.RelatingType
                    break

        if base not in base_details:
            base_details[base] = {
                "type_class": rt.is_a() if rt else f"Ifc{base[3:]}Type" if base.startswith("Ifc") else "IfcTypeObject",
                "type_name_counts": Counter(),
                "untyped": 0,
            }

        if rt is not None:
            tname = getattr(rt, "Name", None) or "(unnamed type)"
            base_details[base]["type_name_counts"][tname] += 1
            # Update actual class (more reliable than deriving from base name)
            base_details[base]["type_class"] = rt.is_a()
        else:
            base_details[base]["untyped"] += 1

    # Sort base classes
    if sort == "count":
        sorted_bases = sorted(base_counts.items(), key=lambda x: (-x[1], x[0]))
    else:
        sorted_bases = sorted(base_counts.items(), key=lambda x: x[0])

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    total_elems = len(elements)
    total_typed = 0
    total_untyped = 0
    total_unique_types = 0

    lines = []
    lines.append("List of element types present in the IFC model (IfcElement):")
    lines.append(f"Total elements: {total_elems}")

    for base, count in sorted_bases:
        details = base_details.get(base, {"type_class": "IfcTypeObject", "type_name_counts": Counter(), "untyped": 0})
        tclass = details["type_class"]
        name_counts = details["type_name_counts"]
        untyped = details["untyped"]

        typed_count = sum(name_counts.values())
        uniq_types = len(name_counts)

        total_typed += typed_count
        total_untyped += untyped
        total_unique_types += uniq_types

        lines.append(f"- {base} ({count})")
        lines.append(f"  Types: {tclass} -> {uniq_types} unique; typed elements: {typed_count}")
        for n, c in sorted(name_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  - {n} ({c})")
        if untyped:
            lines.append(f"  Untyped elements: {untyped}")
        lines.append(f"  Total {base}: {count}")
        lines.append("")

    lines.append("Overall totals:")
    lines.append(f"- Typed elements: {total_typed}")
    lines.append(f"- Untyped elements: {total_untyped}")
    lines.append(f"- Unique Ifc…Type used: {total_unique_types}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Compatible return
    return [(b, base_counts[b], None) for b, _ in sorted_bases]

# Get the type name of an element
def get_element_type_name(element) -> str:
    import ifcopenshell.util
    t = ifcopenshell.util.element.get_type(element)
    if t and hasattr(t, "Name"):
        return str(t.Name)
    if hasattr(element, "PredefinedType"):
        return str(getattr(element, "PredefinedType"))
    if hasattr(element, "Name"):
        return str(getattr(element, "Name"))
    return element.is_a()

# Get best matching candidate from list by name similarity
def get_base_quantities(element) -> Dict[str, float]:
    out = {}
    qto = ifc.util.element.get_qto(element)
    for k, v in qto.items():
        if isinstance(v, (int, float)):
            out[k] = float(v)
    return out

# Get extruded depth and profile from direct/mapped geometry
# Best-effort: get extruded depth and profile from direct/mapped geometry.
def _try_get_extrusion_depth_and_profile(element) -> Tuple[Optional[float], Optional[object]]:
    if not getattr(element, "Representation", None):
        return None, None
    try:
        for rep in element.Representation.Representations:
            for item in getattr(rep, "Items", []) or []:
                if item.is_a("IfcExtrudedAreaSolid"):
                    return float(item.Depth), item.SweptArea
                if item.is_a("IfcMappedItem"):
                    mapped = item.MappingSource.MappedRepresentation
                    for mi in mapped.Items:
                        if mi.is_a("IfcExtrudedAreaSolid"):
                            return float(mi.Depth), mi.SweptArea
    except Exception:
        pass
    return None, None

# Get base quantities from IfcElementQuantity: dict with keys AREA, VOLUME, LENGTH."""
def _get_base_quantities(e):
    q = {"AREA": None, "VOLUME": None, "LENGTH": None, "HEIGHT": None}
    for rel in getattr(e, "IsDefinedBy", []) or []:
        if not rel or not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pset = rel.RelatingPropertyDefinition
        if not pset or not pset.is_a("IfcElementQuantity"):
            continue
        for it in getattr(pset, "Quantities", []) or []:
            if it.is_a("IfcQuantityVolume"):
                q["VOLUME"] = float(getattr(it, "VolumeValue", 0.0) or 0.0)
            elif it.is_a("IfcQuantityArea"):
                q["AREA"] = float(getattr(it, "AreaValue", 0.0) or 0.0)
            elif it.is_a("IfcQuantityLength"):
                q["LENGTH"] = float(getattr(it, "LengthValue", 0.0) or 0.0)
                # Se la quantità si chiama "Height", salva anche come HEIGHT
                if getattr(it, "Name", "").lower() == "height":
                    q["HEIGHT"] = float(getattr(it, "LengthValue", 0.0) or 0.0)
    return q

# Normalize unit strings for comparison
def _norm_unit(u: Optional[str]) -> str:
    if not u:
        return "-"
    s = str(u).strip().lower()
    # Map Danish/variants
    if s in {"m³", "m^3", "cubicmeter"}:
        return "m3"
    if s in {"m²", "m^2"}:
        return "m2"
    if s in {"lm", "lbm", "m1"}:
        return "m"
    return s

def get_project_units(model):
    """Return a dict with the project's units for LENGTH, AREA, VOLUME."""
    units = ifcopenshell.api.unit.get_units(model)
    unit_map = {}
    for u in units:
        if hasattr(u, "UnitType"):
            if u.UnitType == "LENGTHUNIT":
                unit_map["LENGTH"] = getattr(u, "Prefix", "") + u.Name if hasattr(u, "Prefix") else u.Name
            elif u.UnitType == "AREAUNIT":
                unit_map["AREA"] = getattr(u, "Prefix", "") + u.Name if hasattr(u, "Prefix") else u.Name
            elif u.UnitType == "VOLUMEUNIT":
                unit_map["VOLUME"] = getattr(u, "Prefix", "") + u.Name if hasattr(u, "Prefix") else u.Name
    return unit_map

# Get quantity for element based on unit
def get_quantity_for_unit(e, unit: str, model=None) -> Optional[float]:
    """
    Compute element quantity according to unit, converting if necessary.
    Requires 'model' argument to detect source units.
    """
    u = _norm_unit(unit)
    if u in {"-", ""}:
        return 1.0
    q = _get_base_quantities(e)

    # Default: assume model units are meters
    source_units = {"LENGTH": "m", "AREA": "m2", "VOLUME": "m3", "HEIGHT": "m"}
    if model is not None:
        detected = get_project_units(model)
        for k in detected:
            # Normalize to m, m2, m3
            if detected[k].lower().startswith("milli"):
                source_units[k] = "mm" if k == "LENGTH" or k == "HEIGHT" else ("mm2" if k == "AREA" else "mm3")
            elif detected[k].lower().startswith("centi"):
                source_units[k] = "cm" if k == "LENGTH" or k == "HEIGHT" else ("cm2" if k == "AREA" else "cm3")
            elif detected[k].lower().startswith("meter"):
                source_units[k] = "m" if k == "LENGTH" or k == "HEIGHT" else ("m2" if k == "AREA" else "m3")

    # Conversion factors
    unit_factors = {
        ("mm", "m"): 0.001,
        ("cm", "m"): 0.01,
        ("m", "m"): 1.0,
        ("mm2", "m2"): 0.000001,
        ("cm2", "m2"): 0.0001,
        ("m2", "m2"): 1.0,
        ("mm3", "m3"): 0.000000001,
        ("cm3", "m3"): 0.000001,
        ("m3", "m3"): 1.0,
    }

    if u == "m":
        val = q["LENGTH"]
        factor = unit_factors.get((source_units["LENGTH"], "m"), 1.0)
        return val * factor if val is not None else None
    if u == "m2":
        val = q["AREA"]
        factor = unit_factors.get((source_units["AREA"], "m2"), 1.0)
        return val * factor if val is not None else None
    if u == "m3":
        val = q["VOLUME"]
        factor = unit_factors.get((source_units["VOLUME"], "m3"), 1.0)
        return val * factor if val is not None else None
    if u == "height":
        val = q["HEIGHT"]
        factor = unit_factors.get((source_units["HEIGHT"], "m"), 1.0)
        return val * factor if val is not None else None

    return 1.0

# Collect elements by specific IFC classes or all IfcElement if empty.
def collect_candidates_by_classes(model, ifc_classes: Tuple[str, ...]) -> List[object]:
    if not ifc_classes:
        return model.by_type("IfcElement")
    out: List[object] = []
    for cls in ifc_classes:
        out.extend(model.by_type(cls))
    return out

# Map elements to CSV rows using type names, producing quantity and cost lines.
def map_elements_to_price_rows_by_type_name(
    model,
    rows: List[Dict[str, str]],
    *,
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    filter_ifc_classes: Tuple[str, ...] = None,
) -> List[Dict[str, object]]:
    idx = build_price_index_by_text(rows, text_col=text_col)

    # Dynamically detect present IFC classes if not provided
    if filter_ifc_classes is None:
        # Get all unique IFC classes from elements in the model
        elements = model.by_type("IfcElement")
        present_classes = set(e.is_a() for e in elements)
        filter_ifc_classes = tuple(sorted(present_classes))

    elements = collect_candidates_by_classes(model, filter_ifc_classes)
    out: List[Dict[str, object]] = []

    for el in elements:
        tname = get_element_type_name(el)
        key = normalize_text(tname)
        row = idx.get(key)
        if not row:
            continue

        unit = (row.get(unit_col) or "-").strip()
        qty = get_quantity_for_unit(el, unit, model=model)
        if qty is None:
            continue

        try:
            unit_cost = parse_decimal_eu(row.get(unit_cost_col, ""))
        except Exception:
            continue

        out.append(
            {
                "element": el,
                "global_id": ifc.util.element.get_guid(el),
                "type_name": tname,
                "row": row,
                "unit": unit,
                "quantity": float(qty),
                "unit_cost": float(unit_cost),
                "line_total": float(qty) * float(unit_cost),
            }
        )

    return out
