Author: Jens Segaert
Company: VDL Bus Roeselare

--------------------------------------------------------------Description-------------------------------------------------------------------

This folder contains 2 scripts:

CAN-viewer: This script let's you see all incoming CAN-messages through interface. The hexadecimal ID, length, data, cycle time and counter is shown for each message. Also a log file is made from all CAN-messages.


Main: This script reads all incoming CAN-messages through CAN-interface. All signals are then decoded using a Database-CAN. The signals and their values are shown in a graphical user interface (GUI).
Also, there is a counter for each signal. A logger file is made too meant for vector CANalyzer 9.0.


--------------------------------------------------------------------------------------------------------------------------------------------

Install python 3.11.5 and needed libraries: 

							pip install python-can
							pip install cantools
							pip install cachetools

What you need to know:
   	- Connect a CAN-interface (peak,vector...) with your pc to receive CAN-data.
	- When running one of the scripts: you have to choose a json-file. The script opens the folder 'Configuration files' in the main    	  folder.
	- A log file is made of all the CAN-messages. This is found in folder 'Log files'.
	- All CAN-databases are put in folder Databases CAN.



