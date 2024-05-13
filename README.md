# Ex0 - GNSS Raw Mesurments

The following project is a solution for the assinment in the next link https://docs.google.com/document/d/1DDLrA2BoJ4RKa4ahbm2prtseBdgM-2C9UbHO-JwSasw/edit

### requirements
simplekml==1.3.6   
there may be more libraries that will need to be downloaded however for simplekml a specific version is needed

### How To Run
1 download the files   
2 create a python environment project   
3 add all the files to you new project    
4 keep in mind some adjustments may be needed with regards to file path for both reading and writing (code lines 11-15)   
5 from the data folder choose the data log you wish to read and update code line 15 
6 the folder gnssutils in an important folder that is taken from the original source code (very important !)

### source code and information
The code i based on the following notebook you may want to read it to get a better understanding and explanations of the code      
https://www.johnsonmitchelld.com/2021/03/14/least-squares-gps.html

## code breack down
This Python script aims to analyze Global Navigation Satellite System (GNSS) data, calculate satellite positions, perform least squares position solutions, and visualize the results. Let's break down the key components:

1. Data Acquisition and Pre-processing   
The script reads GNSS data from a CSV file, separating raw measurements and Android device fixes.   
It then formats the data, converting timestamps, identifying satellite constellations, and organizing data into epochs.   
2. Satellite Position Calculation   
Satellite positions are calculated using ephemeris data.   
Various corrections, such as satellite clock bias, are applied to refine the positions.   
Doppler shift calculations are performed to account for frequency shifts due to satellite motion.   
3. Least Squares Position Solution   
This part of the script implements a least squares algorithm to estimate the receiver's position.   
It iteratively refines the position estimate based on measured pseudoranges and satellite positions.   
4. Data Analysis and Visualization   
The script analyzes the data to ensure it contains sufficient information for position estimation.   
It then visualizes the results by converting ECEF coordinates to latitude, longitude, and altitude (LLA).   
Key results are saved in CSV files for further analysis or visualization.   
5. Output Generation   
The script generates various outputs, including CSV files containing satellite positions, combined results, and a KML file for visualization in Google Earth.   
6. Main Function   
The main() function orchestrates the entire process, calling different functions to perform specific tasks sequentially.   
