import ifcopenshell as ifc
from collections import defaultdict
import os
from typing import Dict, List, Tuple, Optional
from .helper_read import build_price_index_by_text, normalize_text, parse_decimal_eu

# Nuova funzione: esporta tutti i tipi di elementi presenti nel modello in output/elements.txt
def get_all_struct_elements(model, output_dir="output", filename="elements.txt"):
    """
    Extracts all IfcElement types present in the model and saves them to a TXT file.
    - Creates the 'output' folder if it does not exist.
    - Writes an alphabetically sorted list with a count per type.
    - Returns the list of type names (sorted).
    """
    type_counts = defaultdict(int)

    for elem in model.by_type("IfcElement"):
        type_counts[elem.is_a()] += 1

    sorted_types = sorted(type_counts.items(), key=lambda x: x[0])

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("List of element types present in the IFC model (IfcElement):\n")
        for tname, count in sorted_types:
            f.write(f"- {tname} ({count})\n")

    return [t for t, _ in sorted_types]

# Define function to get rectangle profile from the columns
def get_rectangle_profiles_from_columns(model):
    # Create an empty dictionary to fill with the profile
    profiles_dictionary = {}

    #For every column in all the IfcColumn
    for col in model.by_type("IfcColumn"):
        if not col.Representation: #Check if there aren't
            continue
        
        # Cicle to look the IfcColumn Representations (where the geometry is stored) in Representation
        for rep in col.Representation.Representations:

            # For every items in the representations
            for item in rep.Items:

                # Case 1: if column has direct geometry
                if item.is_a("IfcExtrudedAreaSolid"):
                    # Define the profile using SweptArea
                    profile = item.SweptArea
                    # Check only the rectangle profile
                    if profile.is_a("IfcRectangleProfileDef"):
                        # Get the name of the profile
                        name = profile.ProfileName or "Unnamed"
                        # Look if the profile name is already in the dictionary and if not it creates an empty list
                        if name not in profiles_dictionary:
                            profiles_dictionary[name] = []
                        # Append the profile in the profile name list
                        profiles_dictionary[name].append((col.GlobalId, profile, item.Depth))

                # Case 2: if column uses type geometry (IFC defines the geometry once)
                elif item.is_a("IfcMappedItem"):
                    # Get the MappedRepresentation in MappingSource (the reusable geometry definition)
                    mapped_rep = item.MappingSource.MappedRepresentation
                    # Search for items inside MappedRepresentation
                    for mapped_item in mapped_rep.Items:
                        if mapped_item.is_a("IfcExtrudedAreaSolid"):
                            # Define the profile using SweptArea
                            profile = mapped_item.SweptArea
                            # Check only the rectangle profile
                            if profile.is_a("IfcRectangleProfileDef"):
                                # Get the name of the profile
                                name = profile.ProfileName or "Unnamed"
                                # Look if the profile name is already in the dictionary and if not it creates an empty list
                                if name not in profiles_dictionary:
                                    profiles_dictionary[name] = []
                                # Append the profile in the profile name list
                                profiles_dictionary[name].append((col.GlobalId, profile, mapped_item.Depth))

    return profiles_dictionary

# Define function to get non rectangle profile from the columns
def get_non_rectangle_profiles_from_columns(model):
    profiles_dictionary = {}
    for col in model.by_type("IfcColumn"):
        if not col.Representation:
            continue
        for rep in col.Representation.Representations:
            for item in rep.Items:
                # Profili diversi dal rettangolare
                if item.is_a("IfcExtrudedAreaSolid"):
                    profile = item.SweptArea
                    if not profile.is_a("IfcRectangleProfileDef"):
                        name = profile.ProfileName or profile.is_a() or "Unnamed"
                        if name not in profiles_dictionary:
                            profiles_dictionary[name] = []
                        profiles_dictionary[name].append((col.GlobalId, profile, item.Depth, profile.is_a()))
                elif item.is_a("IfcMappedItem"):
                    mapped_rep = item.MappingSource.MappedRepresentation
                    for mapped_item in mapped_rep.Items:
                        if mapped_item.is_a("IfcExtrudedAreaSolid"):
                            profile = mapped_item.SweptArea
                            if not profile.is_a("IfcRectangleProfileDef"):
                                name = profile.ProfileName or profile.is_a() or "Unnamed"
                                if name not in profiles_dictionary:
                                    profiles_dictionary[name] = []
                                profiles_dictionary[name].append((col.GlobalId, profile, mapped_item.Depth, profile.is_a()))
    return profiles_dictionary

def get_element_type_name(element) -> str:
    try:
        if getattr(element, "IsTypedBy", None):
            rel = element.IsTypedBy[0]
            t = rel.RelatingType
            return getattr(t, "Name", "") or ""
    except Exception:
        pass
    return ""

def get_base_quantities(element) -> Dict[str, float]:
    out: Dict[str, float] = {}
    try:
        for rel in getattr(element, "IsDefinedBy", []) or []:
            if not rel.is_a("IfcRelDefinesByProperties"):
                continue
            qset = rel.RelatingPropertyDefinition
            if not qset or not qset.is_a("IfcElementQuantity"):
                continue
            for q in getattr(qset, "Quantities", []) or []:
                if q.is_a("IfcQuantityVolume"):
                    out[q.Name] = float(q.VolumeValue)
                elif q.is_a("IfcQuantityLength"):
                    out[q.Name] = float(q.LengthValue)
                elif q.is_a("IfcQuantityArea"):
                    out[q.Name] = float(q.AreaValue)
    except Exception:
        pass
    return out

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

def get_quantity_for_unit(element, unit: str) -> Optional[float]:
    unit = (unit or "").strip().lower()
    qto = get_base_quantities(element)

    if unit in ("m3", "m^3"):
        if "NetVolume" in qto:
            return float(qto["NetVolume"])
        if "GrossVolume" in qto:
            return float(qto["GrossVolume"])
        depth, profile = _try_get_extrusion_depth_and_profile(element)
        try:
            if depth and profile and profile.is_a("IfcRectangleProfileDef"):
                return float(profile.XDim) * float(profile.YDim) * float(depth)
        except Exception:
            pass
        return None

    if unit in ("m", "lm", "lbm"):
        if "NetLength" in qto:
            return float(qto["NetLength"])
        if "GrossLength" in qto:
            return float(qto["GrossLength"])
        depth, _ = _try_get_extrusion_depth_and_profile(element)
        if depth:
            return float(depth)
        return None

    if unit in ("m2", "m²"):
        if "NetArea" in qto:
            return float(qto["NetArea"])
        if "GrossArea" in qto:
            return float(qto["GrossArea"])
        return None

    return None

def collect_candidates_by_classes(model, ifc_classes: Tuple[str, ...]) -> List[object]:
    if not ifc_classes:
        return model.by_type("IfcElement")
    out: List[object] = []
    for cls in ifc_classes:
        out.extend(model.by_type(cls))
    return out

def map_elements_to_price_rows_by_type_name(
    model,
    rows: List[Dict[str, str]],
    *,
    text_col: str = "Text",
    unit_col: str = "Unit",
    unit_cost_col: str = "Unit Cost",
    filter_ifc_classes: Tuple[str, ...] = ("IfcBeam", "IfcColumn", "IfcMember", "IfcSlab", "IfcWall", "IfcWallStandardCase"),
) -> List[Dict[str, object]]:
    idx = build_price_index_by_text(rows, text_col=text_col)
    elements = collect_candidates_by_classes(model, filter_ifc_classes)
    out: List[Dict[str, object]] = []

    for el in elements:
        tname = get_element_type_name(el)
        key = normalize_text(tname)
        row = idx.get(key)
        if not row:
            continue

        unit = (row.get(unit_col) or "").strip()
        qty = get_quantity_for_unit(el, unit)
        if qty is None:
            continue

        try:
            unit_cost = parse_decimal_eu(row.get(unit_cost_col, ""))
        except Exception:
            continue

        out.append({
            "element": el,
            "global_id": el.GlobalId,
            "type_name": tname,
            "row": row,
            "unit": unit,
            "quantity": float(qty),
            "unit_cost": float(unit_cost),
            "line_total": float(qty) * float(unit_cost),
        })

    return out
