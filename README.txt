Author: Jens Segaert
Company: VDL Bus Roeselare

--------------------------------------------------------------Description-------------------------------------------------------------------

This folder contains 2 scripts:

CAN-viewer: This script let's you see all incoming CAN-messages through interface. The hexadecimal ID, length, data, cycle time and counter is shown for each message. Also a log file is made from all CAN-messages.


Main: This script reads all incoming CAN-messages through CAN-interface. All signals are then decoded using a Database-CAN. The signals and their values are shown in a graphical user interface (GUI).
Also, there is a counter for each signal. A logger file is made too meant for vector CANalyzer 9.0.


--------------------------------------------------------------------------------------------------------------------------------------------
Procedure:

1. Install python and needed packages first by clicking on 'Install...  .bat' in folder "Install python" , IMPORTANT: DON'T CLOSE THE WINDOW, the window closes itself when the installation is done.
   When the installing, the python setup exe-file opens. Click on 'Modify' and make sure all Optional features and advanced options are selected.
   
   Note: If python isn't installed correctly. Click on "python-3.11.5-amd64.exe" in the folder. Click on 'Modify' and make sure all optional features and advanced options are selected. Go to the terminal in the folder (cmd) 
          and paste this in the terminal:

                                                                                                pip install python-can
                                                                                                pip install cantools
                                                                                                pip install cachetools

2. What you need to know:
   	- Connect a CAN-interface (peak,vector...) with your pc to receive CAN-data.
	- When running one of the scripts: you have to choose a json-file. The script opens the folder 'Configuration files' in the main    	  folder.
	- A log file is made of all the CAN-messages. This is found in folder 'Log files'.
	- All CAN-databases are put in folder Databases CAN.



