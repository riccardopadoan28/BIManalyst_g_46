# BIManalyst — A3 README

## About the tool

**Claim:**  
BIManalyst addresses the challenge of late discovery of performance and coordination issues in building projects, which often leads to costly rework and delays. The tool aims to detect missing or inconsistent model information and provide actionable metrics early in the design process, allowing teams to prioritize fixes before detailed simulation or construction.

**Where the problem was found:**  
This need was identified during the Use Case Analysis in A2, through stakeholder interviews, model audits, and common BIM QA findings. Frequent issues include incomplete model metadata, missing thermal zones, incorrect element types, inconsistent glazing data, and a lack of simple early-stage performance indicators.

## Description of the tool

BIManalyst is a command-line Python utility that analyzes BIM models (preferably IFC files) to:
- Check model completeness (rooms, levels, element types)
- Extract quantities (floor area, volume, glazing area)
- Flag basic performance risks (missing thermal zones, missing U-values, excessive glazing ratios)
- Suggest next actions for each flagged issue

It uses the IfcOpenShell library to read geometry and properties, applies rule checks based on A2 findings, and generates human-readable and machine-readable reports.

## Workflow of the Application

1️⃣ **Group CSV rows by IFC class**  
   - Rows in the price list CSV are grouped by the "Ifc Match" column (e.g., "IfcWall", "IfcSlab").
   - If the class is empty, the element is skipped.

2️⃣ **For each IfcElement in the model:**  
   - Look up matching CSV rows by element class.
   - Fuzzy-match by the element’s Name.
   - Extract the Identification code.
   - Create or reuse a cost item for that code.
   - Add unit cost if necessary.
   - Create an `IfcRelAssignsToControl` linking the element to the cost item.
   - Uses the official IfcOpenShell API (`control.assign_control`), falling back to manual entity creation if the API is unavailable.

3️⃣ **Generate Reports**  
   - Quantity Take-Off (QTO) and Bill of Quantities (BOQ) reports are created in the `output` folder.

4️⃣ **Save Updated IFC Model**  
   - All changes are saved to a new copy of the IFC file in the `output` folder, with `_cost` appended to the filename (e.g., `project_cost.ifc`). The original IFC file is never overwritten.

## Instructions to run the tool

**Prerequisites:**
- Python 3.8+
- Install dependencies:  
  `pip install -r requirements.txt`
- Input: IFC file exported from your BIM authoring tool (Revit, ArchiCAD, etc.)

**Usage:**
1. Run the main script:
   ```
   python main.py
   ```
2. Enter the path to your IFC model when prompted (or pass it as a command-line argument).
3. Enter the path to your price list CSV file when prompted.
4. The tool will process the model, assign cost data, generate reports, and save the updated IFC file in the `output` folder.

## Advanced Building Design

**Design Stage:**  
- Most useful in Stage B (Schematic Design) and early Stage C (Design Development).  
- Designed to catch omissions and risk factors before detailed engineering and simulation.

**Subjects who might use it:**  
- Architects and design leads  
- BIM managers and coordinators  
- Energy and sustainability consultants (early screening)  
- Quantity surveyors (high-level quantities)  
- MEP and façade engineers (early clash/risk awareness)

**Required information in the model:**  
- Geometry for rooms/spaces and building envelope (walls, slabs, windows, etc.)
- Named levels and room/space elements with area/volume
- Element types (wall, slab, roof, window, door)
- Basic material or property sets (U-values or material names) where available
- Orientation and project north / site context
- Assigned thermal zones or room-to-zone mapping (if not present, the tool will flag it)
- Glazing definitions with area or window geometry
- Metadata: element IDs, names, and parameter sets for traceability

If key properties are missing, the tool will report them and provide recommended minimal values or workflows to populate the model.

## Limitations

- Not a replacement for detailed simulation tools — provides screening and QA only.
- Accuracy depends on the quality and completeness of the input IFC/model.
- Advanced HVAC/component simulation is out of scope.

## Contact / Next steps

- Use the generated checklist to correct the model, then rerun BIManalyst prior to deeper
