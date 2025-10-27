import ifcopenshell as ifc


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
