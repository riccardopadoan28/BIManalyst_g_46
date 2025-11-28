# Group BIManalyst_g_46: A3 Tool

## About the tool
Group BIManalys_g_46 has developed a tool that performs a structural cost estimation, working on a given model starting from a given structural price list. 
The tool:
- Reads .ifc elements and their properties;
- Matches elements to cost items from a CSV price list matching and assign `IfcCostSchedule`;
- Assigns cost data to elements by creating `IfcCostItem` and `IfcCostValue` entities;
- Generates total and detailed by level Quantity Take-Off (QTO) and Bill of Quantities (BOQ) reports in .txt file;
- Saves an updated .ifc file with embedded cost information;
- Saves a JSON file of the total BOQ;

# Advanced Building Design

This tool can be useful after the structural early design stage is completed and as well to assess cost estimation analysis during the design process. It needs a structural .ifc model to perform the calculation and it should be useful to PMs, BIM managers, BIM coordinators, quantity surveyors, cost controllers and to performe due diligence on the project. 

# IDS

**Requirements for model and database:**
In order to properly run the application, the .ifc model should requires this criteria:
1. For all the structural elements the IfcQuantitySet have to be populated: QuantityLenght, QuantityArea, QuantityVolume. For example, for a single beam:

   ```bash
      <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
         <ids:ids xmlns:ids="http://standards.buildingsmart.org/IDS" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/1.0/ids.xsd">
            <ids:info>
               <ids:title>A3_TOOL.py IDS</ids:title>
               <ids:description>IFC structural model validation</ids:description>
               <ids:date>2025-11-24</ids:date>
            </ids:info>
            <ids:specifications>
               <ids:specification ifcVersion="IFC4X3_ADD2" name="Rule_1_IfcBeam">
                     <ids:applicability minOccurs="1" maxOccurs="unbounded">
                        <ids:entity>
                           <ids:name>
                                 <ids:simpleValue>IfcBeam</ids:simpleValue>
                           </ids:name>
                        </ids:entity>
                     </ids:applicability>
                     <ids:requirements>
                        <ids:property>
                           <ids:propertySet>
                                 <ids:simpleValue>Qto_BeamBaseQuantities</ids:simpleValue>
                           </ids:propertySet>
                           <ids:baseName>
                                 <ids:simpleValue>QuantityVolume</ids:simpleValue>
                           </ids:baseName>
                        </ids:property>
                     </ids:requirements>
               </ids:specification>
            </ids:specifications>
         </ids:ids>
   ```
2. Strong correlation between the name of the type in the .ifc model and the name in the price list. For example:

   ```bash
      IfcEntity Name: Rektangulær bjælke (RB)_N:RB200/500:340303
      Price list name: 180 x 360 mm rektangulær betonbjælke
   ``` 
3. The cost estimation performs a material cost estimation, so costs defined in the price list have to be the material unitary cost.
4. The csv price list columns are fixed: Identification Code; Name; IfcMatch; IfcCostValue; Unit.

# Workflow of the Application

1️⃣ **Load IFC Model**  
   - The tool reads the input .ifc file from an absolute path using `ifcopenshell.open()`.
   - Extracts all building elements using `ifc_file.by_type()`.

2️⃣ **Load Price List CSV**  
   - Reads the  file containing cost data.
   - Groups rows by the "Ifc Match" column.
   - Elements with empty class names are skipped.

  ```bash
      Identification Code | Name                                        | IfcMatch | IfcCostValue    | Unit |
      04.10.82,01         | Betonbjælke 200 x 300 mm, ikke synlig flade | IfcBeam  | 4056,05         | m3   |
  ```

3️⃣ **Match Elements to Cost Items**  
   - For each IfcElement in the model:
     - Look up matching .csv rows by element class through IfcMatch column.
     - Use fuzzy string matching on the element's Name to find the best price list match using Python's `difflib.SequenceMatcher`.
     - Extract element properties using `ifcopenshell.util.element.get_psets()` to access property sets.
     - Extract quantities using `ifcopenshell.util.element.get_quantity()` for length, area, or volume.

4️⃣ **Assign Cost Data to Elements**  
   - Create `IfcCostSchedule` using `ifcopenshell.api.run("cost.add_cost_schedule", ...)` to organize cost items.
   - Create or reuse an `IfcCostItem` for each matched identification code using `ifcopenshell.api.run("cost.add_cost_item", ...)`.
   - Create `IfcCostValue` entities with unit costs from the .csv using `ifcopenshell.api.run("cost.add_cost_value", ...)`.
   - Link elements to cost items using `ifcopenshell.api.run("control.assign_control", ...)` to create `IfcRelAssignsToControl` relationships.

5️⃣ **Generate Reports**  
   - **Quantity Take-Off (QTO)**: Lists all elements with their quantities (extracted using `ifcopenshell.util.element` utilities), matched cost items, and unit costs.
   - **Bill of Quantities (BOQ)**: Summarizes total costs by element type and cost item, organized by building storey using `ifcopenshell.util.element.get_container()`.
   - Reports are saved as .txt files in the `output` folder.

6️⃣ **Save Updated IFC Model**  
   - All changes (new cost entities and relationships) are written to a new .ifc file using `ifc_file.write()`.
   - The output files are saved in the `output` folder and the original .ifc file is never modified.

# Instructions to run the tool

**Setup:**
1. Clone the repository:
   ```bash
   git clone https://github.com/riccardopadoan28/BIManalyst_g_46.git
   ```
2. Navigate to the A3 folder:
   ```bash
   cd BIManalyst_g_46/A3
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
**Usage:**
1. Run the application:
   ```
   python A3_TOOL.py
   ```
2. Enter the path to your .ifc model.
3. Enter the path to your price list .csv file.
4. The tool will process the model, assign cost data, generate reports, and save the documents in the `output` folder.

# Process Diagram

![BPMN Workflow Diagram](A3_G_46.svg)

# Example of the results

## Quantity Take Off (QTO)

```text
Quantity Take Off (QTO)
Date: 2025-11-28
Total Elements: 1008

#  | IfcTypeClass      | Type Name                                       | Level                                            | Count
───┼───────────────────┼─────────────────────────────────────────────────┼──────────────────────────────────────────────────┼──────
1  | IfcBeamType       | HEB Bjælke_N:HE260B                             | F_00                                             | 8    
2  | IfcBeamType       | HEB Bjælke_N:HE260B                             | F_01                                             | 48   
3  | IfcBeamType       | HEB Bjælke_N:HE260B                             | F_02                                             | 31   
... (output truncated for brevity) ...
TOTAL COUNT = 1008
```

```text
   QUANTITY TAKE OFF (QTO) – TOTALS ONLY
   Date: 2025-11-28
   Total Elements: 1008

   #  | IfcTypeClass      | Type Name                                       | Count
   ───┼───────────────────┼─────────────────────────────────────────────────┼──────
   1  | IfcBeamType       | HEB Bjælke_N:HE260B                             | 133  
   2  | IfcBeamType       | HEB Bjælke_N:HE300B                             | 14   
   3  | IfcBeamType       | HEB Bjælke_N:HE360B                             | 8    
   ... (output truncated for brevity) ...
   TOTAL COUNT = 1008
```

## Bill Of Quantities (BOQ)
```text
   BILL OF QUANTITIES (BOQ) – TOTALS ONLY
   Date: 2025-11-28

   Item         | Description                                 | Unit | Quantity    | Unit Cost | Total Amount
   ─────────────┼─────────────────────────────────────────────┼──────┼─────────────┼───────────┼─────────────
   04.10.83,01  | 120 x 300 mm rektangulær betonbjælke        | lbm  | 524.4040    | 1929.82   | 1012005.29  
   04.10.82,01  | Betonbjælke 200 x 300 mm, ikke synlig flade | m3   | 12.6570     | 4056.05   | 51337.28    
   ... (output truncated for brevity) ...
   TOTAL: 202685407.60
```

```text
BILL OF QUANTITIES (BOQ)
Date: 2025-11-28

Item         | Description                                 | Unit | Level | Quantity    | Unit Cost | Total Amount
─────────────┼─────────────────────────────────────────────┼──────┼───────┼─────────────┼───────────┼─────────────
04.10.83,01  | 120 x 300 mm rektangulær betonbjælke        | lbm  | B_00  | 169,6600    | 1929,82   | 327413,26   
04.10.83,01  | 120 x 300 mm rektangulær betonbjælke        | lbm  | F_00  | 138,4700    | 1929,82   | 267222,18   
... (output truncated for brevity) ...
TOTAL: 202685407.60
```
## JSON FILE
```text
{
  "document": {
    "title": "BILL OF QUANTITIES (BOQ) – TOTALS ONLY",
    "date": "2025-11-28",
    "source": "IFC Model Analysis"
  },
  "items": [
    {
      "itemCode": "04.10.83,01",
      "description": "120 x 300 mm rektangulær betonbjælke",
      "unit": "lbm",
      "quantity": 524.404,
      "unitCost": 1929.82,
      "totalAmount": 1012005.29
    },
    ... (output truncated for brevity) ...
```

# Future perspective

1. Implement the logic of matching also for kg, stk.
2. Assign to the IfcCostItem also the costs of equipment rents and labours.

# Reference

**IfcOpenShell 0.8.4 Documentation:**
- [IfcOpenShell Util](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/index.html)
- [IfcOpenShell Cost API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/cost/index.html)

**IFC4x3_ADD2 Documentation:**
- [IfcCostSchedule](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCostSchedule.htm)
- [IfcCostItem](https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcCostItem.htm)
- [IfcCostValue](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcCostValue.htm)


