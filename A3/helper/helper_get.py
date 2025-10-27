import ifcopenshell as ifc

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
