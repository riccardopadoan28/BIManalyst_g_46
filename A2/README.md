# BIManalyst group 46

## A2a

Group: 46
I am confident coding in Python: 2 - Neutral
Focus Area: Build - Analyst

##A2b

Building #2508
Claim: "The client read the page 3 of the 25-08-D-PM report from folder CES_BLD_25_08 and would like to check the structural elements sales price reported in "Figure 5: Sigma Estimation" to verify that the budget set is met"

## A2c

This claim would be checked when:
1.  The works for the structure needs to be agreed with the sub-constructor;
2.  The design team have to verify the tendering budget before apply for tendering;
3.  The stakeholders involved have to check the cash flows in the early construction phase.

Phase: Design, Tendering, Build

To pursuit the claim the user need to:
1.  gather the structural elements;
2.  extract quantity take off and generate QTO report;
3.  analyze and gather prices from price lists;
4.  assign correct price to the structural elements;
5.  calculate bill of quantities and generate BOQ report.

## BPMN file
You can see the documentation [here][a2ImageLink]
[a2ImageLink]: IMG/A2_G_46.svg

IFC Classes involved would be: IfcBeams, IfcColumns, IfcSlabs, IfcWalls, ecc..

## A2d


## A2e

The tool analyze the IFC model to classify each structural element by category and level. A price materal dictionary is created by the user to analyze the budget for the structural area of the buildings.
The society value of the tools is to being able to analyze the structural cost, making easy to identify the implication of price changes of the materials on the design, tendering and construction process.

## A2f

A2f: Information Requirements
Identify what information you need to extract from the model

Where is this in IFC?

Is it in the model?

Do you know how to get it in ifcOpenShell?

What will you need to learn to do this? [Enrolled students only]: add to this excel in teams
