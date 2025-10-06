# BIManalyst group 46

Group: 46

Focus Area: Build

Claims: "The client read the page 14 of the 25-08-D-STR report from folder CES_BLD_25_08 and would like to check the profiles of the rectangular columns in the model, assuming that the material is correct."

The script developed:
1) import the ifcopenshell library;
2) open the 25-08-D-STR.ifc file;
3) define a function to get the rectangular column profiles;
4) extract all the columns modeled and fill an empty dictionary with the information grouped by profile name;
5) call that function in the main and get the information;
6) write the output.

Output:
1) from the terminal the user can check out if there are any disalignment between profile name and dimensions;
2) the user can check out if there are any lack of communication between the model and the report.