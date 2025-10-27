import ifcopenshell as ifc


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