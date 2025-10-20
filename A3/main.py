# Import ifcopenshell
import ifcopenshell as ifc
import ifcopenshell
from collections import defaultdict


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

# Define the total volume of the columns by level
def get_total_volume_by_level(model):
    level_volumes = {}
    total_volume = 0.0
    for col in model.by_type("IfcColumn"):
        if not col.Representation:
            continue
        # Trova il livello tramite relazioni spaziali
        level_name = "Unknown"
        for rel in getattr(col, "ContainedInStructure", []):
            if rel.RelatingStructure and hasattr(rel.RelatingStructure, "Name"):
                level_name = rel.RelatingStructure.Name or "Unknown"
        # Cerca la geometria rettangolare
        for rep in col.Representation.Representations:
            for item in rep.Items:
                if item.is_a("IfcExtrudedAreaSolid"):
                    profile = item.SweptArea
                    if profile.is_a("IfcRectangleProfileDef"):
                        x = profile.XDim
                        y = profile.YDim
                        depth = item.Depth
                        volume = (x / 1000.0) * (y / 1000.0) * (depth / 1000.0) # m³
                        level_volumes.setdefault(level_name, 0.0)
                        level_volumes[level_name] += volume
                        total_volume += volume
                elif item.is_a("IfcMappedItem"):
                    mapped_rep = item.MappingSource.MappedRepresentation
                    for mapped_item in mapped_rep.Items:
                        if mapped_item.is_a("IfcExtrudedAreaSolid"):
                            profile = mapped_item.SweptArea
                            if profile.is_a("IfcRectangleProfileDef"):
                                x = profile.XDim
                                y = profile.YDim
                                depth = mapped_item.Depth
                                volume = (x / 1000.0) * (y / 1000.0) * (depth / 1000.0) # m³
                                level_volumes.setdefault(level_name, 0.0)
                                level_volumes[level_name] += volume
                                total_volume += volume
    return level_volumes, total_volume

# Read material prices from a text file
def read_material_prices(file_path="Price_List.txt"):
    prices = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if '=' in line:
                    material, price = line.strip().split('=')
                    prices[material.strip()] = float(price.strip())
    except FileNotFoundError:
        pass
    return prices

# Write the results in a txt file
def write_qto_columns(grouped, file_path="QTO_Columns.txt", material="Concrete", prices=None):
    if prices is None:
        prices = {}
    price_per_m3 = prices.get(material, 0)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("Profile Name | Column ID | XDim [mm] | YDim [mm] | Depth [mm] | Volume [m³] | Material | Price [€]\n")
        f.write("-" * 120 + "\n")
        for profile_name in sorted(grouped.keys()):
            for col_id, profile, depth in grouped[profile_name]:
                x = profile.XDim
                y = profile.YDim
                d = depth
                volume = (x / 1000.0) * (y / 1000.0) * (d / 1000.0)
                price = round(volume * price_per_m3, 2)
                f.write(f"{profile_name} | {col_id} | {round(x,2)} | {round(y,2)} | {round(d,2)} | {round(volume,2)} | {material} | {price}\n")

def write_qto_columns_all(grouped_rect, grouped_nonrect, file_path="QTO_Columns.txt", prices=None):
    if prices is None:
        prices = {}
    steel_count_by_level = {}
    steel_total_count = 0
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("Profile Name | Column ID | XDim [mm] | YDim [mm] | Depth [mm] | Volume [m³] | Material | Price [€]\n")
        f.write("-" * 120 + "\n")
        # Rettangolari (Concrete)
        for profile_name in sorted(grouped_rect.keys()):
            price_per_m3 = prices.get("Concrete", 0)
            for col_id, profile, depth in grouped_rect[profile_name]:
                x = profile.XDim
                y = profile.YDim
                d = depth
                volume = (x / 1000.0) * (y / 1000.0) * (d / 1000.0)
                price = round(volume * price_per_m3, 2)
                f.write(f"{profile_name} | {col_id} | {round(x,2)} | {round(y,2)} | {round(d,2)} | {round(volume,2)} | Concrete | {price}\n")
        # Non rettangolari (Steel)
        for profile_name in sorted(grouped_nonrect.keys()):
            price_per_meter = prices.get(profile_name, prices.get("Steel", 0))
            for col_id, profile, depth, profile_type in grouped_nonrect[profile_name]:
                d = depth / 1000.0  # lunghezza in metri
                # Calcolo volume per profili circolari
                if profile_type == "IfcCircleProfileDef":
                    r = profile.Radius
                    volume = 3.1416 * (r / 1000.0) ** 2 * d
                else:
                    volume = 0.0
                price = round(price_per_meter * d, 2)
                x = getattr(profile, "XDim", "-")
                y = getattr(profile, "YDim", "-")
                f.write(f"{profile_name} | {col_id} | {x} | {y} | {round(depth,2)} | {round(volume,2)} | Steel | {price}\n")
                # Conteggio per livello
                level_name = "Unknown"
                if hasattr(profile, "ContainedInStructure"):
                    for rel in getattr(profile, "ContainedInStructure", []):
                        if rel.RelatingStructure and hasattr(rel.RelatingStructure, "Name"):
                            level_name = rel.RelatingStructure.Name or "Unknown"
                steel_count_by_level.setdefault(level_name, 0)
                steel_count_by_level[level_name] += 1
                steel_total_count += 1
        f.write(f"\nTotal steel columns count: {steel_total_count}\n")
        for level in steel_count_by_level:
            f.write(f"Steel columns count at level {level}: {steel_count_by_level[level]}\n")

def write_boq_columns(level_volumes, total_volume, prices, grouped_nonrect=None, file_path="BOQ_Columns.txt"):
    price_per_m3 = prices.get("Concrete", 0)
    steel_total_price = 0.0
    steel_level_prices = {}
    steel_count_by_level = {}
    steel_total_count = 0
    # Calcolo prezzi e conteggi per colonne acciaio se presenti
    if grouped_nonrect:
        for profile_name in grouped_nonrect:
            price_per_meter = prices.get(profile_name, prices.get("Steel", 0))
            for col_id, profile, depth, profile_type in grouped_nonrect[profile_name]:
                d = depth / 1000.0  # lunghezza in metri
                price = round(price_per_meter * d, 2)
                # Trova livello
                level_name = "Unknown"
                if hasattr(profile, "ContainedInStructure"):
                    for rel in getattr(profile, "ContainedInStructure", []):
                        if rel.RelatingStructure and hasattr(rel.RelatingStructure, "Name"):
                            level_name = rel.RelatingStructure.Name or "Unknown"
                steel_level_prices.setdefault(level_name, 0.0)
                steel_level_prices[level_name] += price
                steel_count_by_level.setdefault(level_name, 0)
                steel_count_by_level[level_name] += 1
                steel_total_price += price
                steel_total_count += 1
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Level | Total Volume [m³] | Total Price [€] | Steel Columns Count\n")
        f.write("-" * 60 + "\n")
        for level in sorted(level_volumes.keys()):
            vol = level_volumes[level]
            price = round(vol * price_per_m3, 2)
            steel_price = round(steel_level_prices.get(level, 0.0), 2)
            steel_count = steel_count_by_level.get(level, 0)
            f.write(f"{level} | {round(vol,2)} | {price} (Concrete) | {steel_price} (Steel) | {steel_count}\n")
        total_price = round(total_volume * price_per_m3, 2)
        f.write("\nTotal rectangular column volume: {} m³\n".format(round(total_volume,2)))
        f.write("Total price (Concrete): {} €\n".format(total_price))
        f.write("Total price (Steel): {} €\n".format(round(steel_total_price,2)))
        f.write(f"Total steel columns count: {steel_total_count}\n")


# Define main
def main():
    # Assign the file to the model variable using file path
    model = ifc.open(r"C:\Users\ricki\Desktop\GitHub\BIManalyst_g_46\A2\25-08-D-STR.ifc")

    #Call the funtion to get the profiles dictionary
    grouped_rect = get_rectangle_profiles_from_columns(model)
    grouped_nonrect = get_non_rectangle_profiles_from_columns(model)

    # Stampa volume totale per livello colonne
    level_volumes, total_volume = get_total_volume_by_level(model)
    print("Total column volume by level:")
    for level, vol in level_volumes.items():
        print(f"  Level: {level} -> Volume: {round(vol, 2)} m³")
    print(f"Total rectangular column volume: {round(total_volume, 2)} m³")
    # Write results to ordered txt file in English
    with open("QTO_Columns.txt", "w", encoding="utf-8") as f:
        f.write("Total column volume by level (sum of individual elements, dimensions in millimeters):\n")
        for level in sorted(level_volumes.keys()):
            f.write(f"  Level: {level} -> Volume: {round(level_volumes[level], 2)} m³\n")
        f.write(f"Total rectangular column volume (sum of all elements): {round(total_volume, 2)} m³\n\n")
    material_prices = read_material_prices()
    write_qto_columns_all(grouped_rect, grouped_nonrect, file_path="QTO_Columns.txt", prices=material_prices)
    write_boq_columns(level_volumes, total_volume, material_prices, grouped_nonrect=grouped_nonrect)
    total_price = round(total_volume * material_prices.get("Concrete", 0), 2)
    print(f"Total price for all columns: {total_price} €")
    print("Final results written to QTO_Columns.txt and BOQ_Columns.txt. Details of individual columns are visible in the txt file.")

if __name__ == "__main__":
    main()