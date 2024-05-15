# Ex0 - GNSS Raw Measurements
The following project is a solution for the assignment in the next link:
[assignment 0](https://docs.google.com/document/d/1DDLrA2BoJ4RKa4ahbm2prtseBdgM-2C9UbHO-JwSasw/edit)

## authorers
zeev fischer: 318960242   
eden mor: 316160332   
daniel musai: 206684755   

### How To Run
1 Download the files   
2 Create a Python environment project (the project name used in this code is "pythonProject1")   
3 Add all the files to your new project   
4 Keep in mind some adjustments may be needed with regards to file path for both reading and writing (code lines 11-15 in main.py)    
5 From the data folder, choose the data log you wish to read and update code line 15 with the file name       
6 The folder gnssutils is an important folder that is taken from the original source code do not forget to add it (very important !)   
7 at the end all fiels will be created in the "output" folder if not go back to code lines 11-15 to update the code

### Requirements
~~~
pip install -r requirements.txt 
~~~
* you may use the following command to install all the requirements i had in my project keep in mined that there may be un nesessery downlowads there!    
* simplekml==1.3.6   (this is important)
* There may be more libraries that will need to be downloaded if you do not run the above command. However, for simplekml, a specific version is needed.

### Source Code and Information
The code is based on the following notebook. You may want to read it to get a better understanding and explanations of the code:   
[Calculating Your Android's Position from Raw GNSS Pseudorange Measurements](https://www.johnsonmitchelld.com/2021/03/14/least-squares-gps.html)   

### location algorithm
The receiver gathers data from multiple satellites, including the time it takes for signals to travel from each satellite to the receiver (pseudorange).
 The algorithm starts with an initial estimate of the receiver's location and clock bias (difference between the receiver's clock and the satellite's clock).
It iterates through the collected data in time segments called epochs. For each epoch:

It selects the satellite measurements available within that time segment.
It ensures there are enough satellite measurements (at least four) to accurately estimate the receiver's location.
Using information about the satellites' orbits and clocks (ephemeris data), the algorithm calculates the expected pseudorange for each satellite based on the current estimate of the receiver's location.
 Employing a mathematical technique called least squares, the algorithm adjusts the receiver's estimated location and clock bias to minimize the difference between the expected pseudoranges and the actual measured pseudoranges.
This adjustment process iterates until the estimated receiver location converges to a stable solution.
The algorithm provides a list of estimated receiver locations for each epoch, offering a trajectory of the receiver's movement over time.
