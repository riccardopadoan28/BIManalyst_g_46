# Group BIManalyst_g_46: A3 Tool

## About the tool
Group BIManalys_g_46 has developed a tool that perform a structural cost estimation, working on a given model starting from a given structural price list. 
The tool:
- Reads .ifc elements and their properties;
- Matches elements to cost items from a CSV price list matching and assign `IfcCostSchedule`;
- Assigns cost data to elements by creating `IfcCostItem` and `IfcCostValue` entities;
- Generates total and detailed by level Quantity Take-Off (QTO) and Bill of Quantities (BOQ) reports in .txt file;
- Saves an updated .ifc file with embedded cost information;
- Saves a JSON file of the total BOQ;

# Advanced Building Design

This tool can be useful after the structural early design stage is completed and as well to assess cost estimation analysis during the design process. It needs a structural ifc model to perform the calculation and it should be useful to PMs, BIM managers, BIM coordinators, quantity surveyors, cost controllers and to performe due diligence on the project. 

**Requirements for model and database:**
In order to properly run the application, the .ifc model should requires this criteria:
- All Elements QuantitySet have to be populated: QuantityLenght, QuantityArea, QuantityVolume;
- Strong correlation between the name of the type in the .ifc model and the name in the price list;
- The cost defined in the price list (Unit Cost) has to be the unitary cost.

# Workflow of the Application

1️⃣ **Load IFC Model**  
   - The tool reads the input .ifc file from an absolute path using `ifcopenshell.open()`.
   - Extracts all building elements using `ifc_file.by_type()`.

2️⃣ **Load Price List CSV**  
   - Reads the  file containing cost data.
   - Groups rows by the "Ifc Match" column.
   - Elements with empty class names are skipped.

  ```bash
      Identification Code | Name         | IfcMatch | IfcCostValue    | Unit |
      04.10.82,01         | Betonbjaelke | IfcBeam  | 4056,05         | m3   |
  ```

3️⃣ **Match Elements to Cost Items**  
   - For each IfcElement in the model:
     - Look up matching .csv rows by element class through IfcMatch column.
     - Use fuzzy string matching on the element's Name to find the best price list match (using Python's `difflib.SequenceMatcher`)
     - Extract element properties using `ifcopenshell.util.element.get_psets()` to access property sets.
     - Extract quantities using `ifcopenshell.util.element.get_quantity()` for length, area, or volume.

4️⃣ **Assign Cost Data to Elements**  
   - Create `IfcCostSchedule` using `ifcopenshell.api.run("cost.add_cost_schedule", ...)` to organize cost items.
   - Create or reuse an `IfcCostItem` for each matched identification code using `ifcopenshell.api.run("cost.add_cost_item", ...)`.
   - Create `IfcCostValue` entities with unit costs from the CSV using `ifcopenshell.api.run("cost.add_cost_value", ...)`.
   - Link elements to cost items using `ifcopenshell.api.run("control.assign_control", ...)` to create `IfcRelAssignsToControl` relationships.

5️⃣ **Generate Reports**  
   - **Quantity Take-Off (QTO)**: Lists all elements with their quantities (extracted using `ifcopenshell.util.element` utilities), matched cost items, and unit costs.
   - **Bill of Quantities (BOQ)**: Summarizes total costs by element type and cost item, organized by building storey using `ifcopenshell.util.element.get_container()`.
   - Reports are saved as CSV files in the `output` folder.

6️⃣ **Save Updated IFC Model**  
   - All changes (new cost entities and relationships) are written to a new IFC file using `ifc_file.write()`.
   - The output file is saved in the `output` folder with `_cost` appended to the filename (e.g., `project_cost.ifc`).
   - The original IFC file is never modified.

# Instructions to run the tool

**Usage:**
1. Run the main script:
   ```
   python A3_TOOL.py
   ```
2. Enter the path to your IFC model when prompted (or pass it as a command-line argument).
3. Enter the path to your price list CSV file when prompted.
4. The tool will process the model, assign cost data, generate reports, and save the outputs in the `output` folder.

# Process Diagram

![BPMN Workflow Diagram](A3_G_46.svg)

# Reference

**IfcOpenShell 0.8.4 Documentation:**
- [IfcOpenShell Util](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/index.html)
- [IfcOpenShell Cost API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/cost/index.html)

**IFC4x3_ADD2 Documentation:**
- [IfcCostSchedule](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCostSchedule.htm)
- [IfcCostItem](https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcCostItem.htm)
- [IfcCostValue](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCostValue.htm)


