# BIManalyst — A3 README

## About the tool
BIManalyst is a lightweight analysis tool that extracts building information from a BIM model to identify early-stage design issues and provide quantifiable indicators (area, volume, glazing ratio, thermal zones, basic energy and daylight risk flags). It is intended to reduce iteration time by surfacing model gaps and common performance risks before detailed simulation.

Problem / claim
- Many projects discover performance and coordination problems late, causing rework and cost growth. BIManalyst claims to detect missing or inconsistent model information and provide simple, actionable metrics early so design teams can prioritise fixes.

Where the problem was found
- The problem was identified from the Use Case Analysis in A2 (project stakeholder interviews, model audits and common BIM QA findings): incomplete model metadata, missing thermal zones, wrong element types, inconsistent glazing data and lack of simple early-stage performance indicators.

## Description of the tool
- Input: a BIM export (IFC recommended) or an equivalent structured model file.
- Output: a compact report (Markdown / JSON / CSV) listing:
    - Model completeness checklist (rooms, levels, element types)
    - Quantities: gross floor area, conditioned volume, glazing area
    - Basic performance flags: missing thermal zones, missing material U-values, excessive glazing ratio in façades
    - Suggested next actions for each flag
- Implementation: command-line Python utility that uses an IFC parsing library to read geometry and element properties, applies rule checks derived from the A2 use case analysis, and emits human-readable and machine-readable reports.

## Instructions to run the tool
Prerequisites
- Python 3.8+
- Install requirements: pip install -r requirements.txt
- Input: provide an IFC file exported from your BIM authoring tool (Revit, ArchiCAD, etc.)

Example usage
- Analyze a model and generate a Markdown report:
    - python analyze.py --input project.ifc --output report.md
- Generate JSON for downstream tools:
    - python analyze.py --input project.ifc --output report.json --format json
- Quick check (prints summary to console):
    - python analyze.py --input project.ifc --quick

Notes
- If using Revit or other proprietary formats, export to IFC or another supported exchange format first.
- See the CLI help for full option list: python analyze.py --help

## Advanced Building Design stage
Primary stage: B — Schematic design
- The tool is most useful in early schematic and design-development stages (B and early C). It is designed to catch omissions and risk factors before detailed engineering and simulations.

## Who should use it
- Architects and design leads
- BIM managers and coordinators
- Energy and sustainability consultants (early screening)
- Quantity surveyors (high-level quantities)
- MEP and façade engineers (early clash/risk awareness)

## Required information in the model
For reliable results the model should include:
- Geometry for rooms/spaces and building envelope (faces, walls, windows)
- Named levels and room/space elements with area/volume
- Element types (wall, slab, roof, window, door)
- Basic material or property sets (U-values or material names) where available
- Orientation and project north / site context
- Assigned thermal zones or at least room-to-zone mapping (if not present the tool will flag it)
- Glazing definitions that include outer area or window geometry
- Metadata: element IDs, names, and parameter sets for traceability

If key properties are missing the tool will report them and provide recommended minimal values or workflows to populate the model.

## Limitations
- Not a replacement for detailed simulation tools — it provides screening and QA only.
- Accuracy depends on the quality and completeness of the input IFC/model.
- Advanced HVAC/component simulation is out of scope.

## Contact / Next steps
- Use the generated checklist to correct the model, then rerun BIManalyst prior to deeper simulation or contractor handover.
