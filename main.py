import ifcopenshell as ifc

def get_column_type_names(model):
    # Get the column type
    columns_type=model.by_type("IfcColumnType")
    # Warning message
    if columns_type is None:
        print("Warning! No IfcColumnType found in the model!")
    else:
        #print(columns_type) is not needed

        # Define an empty dictionary to fill with column type names
        column_type_names = []
        for column_type in columns_type:
            column_type_name = column_type.Name 
            column_type_names.append(column_type_name)   
    return column_type_names

#def create_column_dict():
    #int number
    #print("How many Column Types does the report define?")
    

def main():
    # Get the model from the path
    model=ifc.open(r"C:\Users\ricki\Desktop\GitHub\BIManalyst_g_46\25-08-D-STR.ifc")
    # Define the building
    building=model.by_type("IfcBuilding")
    # Warning message
    if building is None:
        print("Warning! No IfcBuilding found in the model!")
    
    #dictionary=create_column_dict()

    # Use the function to get_column_type_names and print it 
    print(get_column_type_names(model))


    main()
