# BIManalyst group 46

Group: 46

Focus Area: Build

Claims: "The client read the page 14 of the 25-08-D-STR report from folder CES_BLD_25_08 and would like to verify that the columns modeled are all described in the table."

The script developed:
1) import the ifcopenshell library;
2) open the 25-08-D-STR.ifc file;
3) define the building using IfcBuilding;
4) extract all the type of columns modeled in the building;
5) check out if there are any lack of communication between model and report: an empty dictionary is filled with column type names

In the next:
6) try to check out the profiles of the columns.
