# Import ifcopenshell
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
                        profiles_dictionary[name].append((col.GlobalId, profile))

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
                                profiles_dictionary[name].append((col.GlobalId, profile))

    return profiles_dictionary

# Define main
def main():
    # Assign the file to the model variable using file path
    model = ifc.open(r"C:\Users\ricki\Desktop\GitHub\BIManalyst_g_46\25-08-D-STR.ifc")

    #Call the funtion to get the profiles dictionary
    grouped = get_rectangle_profiles_from_columns(model)

    # For the items in the 
    for profile_name, col_profiles in grouped.items():
        print(f"Profile Name: {profile_name}")
        #Get the information from col_profiles
        for col_id, profile in col_profiles:
            print(f"  Column {col_id}")
            print(f"    XDim: {profile.XDim}")
            print(f"    YDim: {profile.YDim}")

        # To divide the profile list in the terminal
        print("-" * 40)

if __name__ == "__main__":
    main()