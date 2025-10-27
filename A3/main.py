# Importations
import ifcopenshell as ifc

# Function to get total volume by level
from collections import defaultdict
from helper.helper_get import get_rectangle_profiles_from_columns, get_non_rectangle_profiles_from_columns, get_total_volume_by_level
from helper.helper_read import read_material_prices
from helper.helper_write import write_qto_columns_all, write_boq_columns


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