"""
Author: Jens Segaert
Company: VDL Bus Roeselare

Python version: 3.11.5

Description: This script let's you see all incoming CAN-messages through interface.
The hexadecimal ID, length, data, cycle time and counter is shown for each message.
Also, a log file is made from all the CAN-messages in the folder "Log files".
"""

import tkinter as tk
from tkinter import ttk
import can
import json
import threading
import time
from tkinter import filedialog
import os
import datetime
import atexit


# Dictionary to hold message info
message_data = {}

# Een lock voor synchronisatie van toegang tot message_data
message_data_lock = threading.Lock()

can_configurations = []



def load_json():
    global config_data

    # Set current directory
    current_directory = os.getcwd() + "\\Configuration files"

    # Search all JSON-files in folder
    json_files = [f for f in os.listdir(current_directory) if f.endswith(".json")]

    if len(json_files) == 1:
        # If there is only 1 JSON-file, load this immediately
        json_filename = json_files[0]
    else:
        # Show GUI to choose JSON-file
        root = tk.Tk()
        root.withdraw()  # Hide window GUI

        json_filename = filedialog.askopenfilename(
            initialdir=current_directory,
            title="Selecteer een JSON-configuratiebestand",
            filetypes=(("JSON-bestanden", "*.json"), ("Alle bestanden", "*.*"))
        )

    if json_filename:
        # Load selected JSON-file
        with open(json_filename, 'r') as json_file:
            config_data = json.load(json_file)
        return config_data
    else:
        print("No JSON-file found.")
        return None



# Function to setup CAN-buses
def setup_can_buses():
    global can_configurations
    for i in range(1, 7):
        interface_key = f"Interface{i}"
        channel_key = f"Channel{i}"
        bitrate_key = f"Bitrate{i}"

        interface = config_data.get(interface_key)
        channel = config_data.get(channel_key)
        bitrate = config_data.get(bitrate_key)

        if interface and channel and bitrate:
            can_configurations.append((interface, channel, bitrate))



# Function to create the GUI
def create_gui():
    global root, treeview
    # Make tkinter window
    root = tk.Tk()
    root.title("CAN Message Viewer")
    root.state('zoomed')
    root.geometry("800x600")  # Change geometry

    treeview = ttk.Treeview(root, columns=("ID", "Length", "Data", "Cycle Time", "Count"), show="headings")
    treeview.heading("ID", text="ID")
    treeview.heading("Length", text="Length")
    treeview.heading("Data", text="Data")
    treeview.heading("Cycle Time", text="Cycle Time (ms)")
    treeview.heading("Count", text="Count")

    treeview.config(height=1200)

    treeview.pack()



# Function to create log file in path
def create_log_file_path():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    logger_directory = os.path.join(script_directory, "Log files")
    if not os.path.exists(logger_directory):
        os.makedirs(logger_directory)
    timestamp = datetime.datetime.now().strftime("%d %b %Y %Ih-%Mmin-%Ssec")
    timestamp = timestamp.replace(":", "-").replace(" ", "_").replace(".", "-")
    log_file_path = os.path.join(logger_directory, f"can_log_{timestamp}.asc")
    return log_file_path



# Init-function
def init():
    global log_file, start_time_logger

    # Call function load_json()
    load_json()

    # Call function setup_can_buses()
    setup_can_buses()

    # Call function create_gui()
    create_gui()

    # Create log file path en open file
    log_file_path = create_log_file_path()
    log_file = open(log_file_path, "a")

    # Initialise in log file:
    timestamp = datetime.datetime.now().strftime("%a %b %d %I:%M:%S.%f")[:-3] + datetime.datetime.now().strftime(
        " %p %Y")
    timestamp = timestamp.replace("AM", "am").replace("PM", "pm")

    log_file.write("date " + f"{timestamp}\n")
    log_file.write("base hex  timestamps absolute\n")
    log_file.write("internal events logged\n")
    log_file.write("// version 9.0.0\n")
    log_file.write("Begin Triggerblock " + f"{timestamp}\n")
    start_time_logger = time.perf_counter()
    log_file.write(f"   0.000000" + " Start of measurement\n")





# Function to format message to put in logger file
def format_message_for_log_file(message, start_time_logger):
    timestamp = time.perf_counter() - start_time_logger
    hex_data = ' '.join([f"{byte:02X}" for byte in message.data])
    message_channel = message.channel + 1
    ID_for_log_file = f'{message.arbitration_id:08X}x'

    return f"{timestamp:.6f} {message_channel}  {ID_for_log_file}       Rx   d {message.dlc} {hex_data}"



# Function to receive CAN-messages and save
def receive_can_messages(bus):
    while True:

        message = bus.recv()

        if message is not None and not message.is_error_frame:
            message_id = hex(message.arbitration_id)
            with message_data_lock:
                if message_id in message_data:
                    # Calculate cycle time based on timestamps
                    current_time = message.timestamp  # Use timestamp of message
                    last_time = message_data[message_id]['last_time']
                    cycle_time = current_time - last_time
                    message_data[message_id]['last_time'] = current_time
                    message_data[message_id]['cycle_time'] = round(cycle_time * 1000, 1)
                    message_data[message_id]['count'] += 1
                    message_data[message_id]['data'] = ' '.join(f"{byte:02X}" for byte in message.data)
                    message_data[message_id]['length'] = len(message.data)
                else:
                    # Save message in dictionary
                    message_data[message_id] = {
                        'message': message,
                        'last_time': message.timestamp,  # Gebruik de timestamp van het bericht
                        'cycle_time': 0,
                        'count': 1,
                        'data': ' '.join(f"{byte:02X}" for byte in message.data),
                        'length': len(message.data)
                    }
                # Write the CAN message to the log file
                timestamp = datetime.datetime.now().strftime("%a %b %d %I:%M:%S.%f %p %Y")[:-6].lower()
                message_for_log_file = format_message_for_log_file(message, start_time_logger)
                log_file.write(f"   {message_for_log_file} \n")




# Function to update GUI with CAN-messages
def update_gui(treeview, message_id):
    with message_data_lock:
        message = message_data[message_id]['message']
        message_length = message_data[message_id]['length']
        message_data_text = message_data[message_id]['data']
        cycle_time = message_data[message_id]['cycle_time']
        count = message_data[message_id]['count']

    for item in treeview.get_children():
        if treeview.item(item, 'values')[0] == message_id:
            current_values = treeview.item(item, 'values')
            treeview.item(item, values=(message_id, message_length, message_data_text, cycle_time, count))
            return

    treeview.insert('', 'end', values=(message_id, message_length, message_data_text, cycle_time, count))



# Create a thread for periodically updating the GUI
def update_gui_thread():
    while True:
        message_ids = list(message_data.keys())  # Create a copy of keys
        for message_id in message_ids:
            update_gui(treeview, message_id)
        time.sleep(0.2)




# If program exits, end the logger file
def exit_handler():
    if log_file is not None and not log_file.closed:
        log_file.write("End TriggerBlock\n")
        log_file.close()


# Main-function
def main():

    # Function to initialise
    init()

    # Create a thread for receiving CAN-messages
    receive_threads = []
    for config in can_configurations:
        interface, channel, bitrate = config
        bus = can.interface.Bus(bustype=interface, channel=channel, bitrate=bitrate)

        receive_thread = threading.Thread(target=receive_can_messages, args=(bus,))
        receive_thread.daemon = True
        receive_thread.start()
        receive_threads.append(receive_thread)


    # Call function update_gui_thread in an other thread
    update_thread = threading.Thread(target=update_gui_thread)
    update_thread.daemon = True
    update_thread.start()

    # Register the exit handler
    atexit.register(exit_handler)

    root.mainloop()



# Start Main-function
if __name__ == "__main__":
    main()


