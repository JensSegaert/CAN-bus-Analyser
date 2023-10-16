"""
Author: Jens Segaert
Company: VDL Bus Roeselare

Python version: 3.11.5

Description: This script reads all incoming CAN-messages through CAN-interface.
All signals are then decoded using a Database-CAN.
The signals and their values are shown in a graphical user interface (GUI).
Also, there is a counter for each signal.
A logger file is made meant for vector CANalyzer 9.0 in the folder "Log files".
"""


import cantools
import os
import can
import tkinter as tk
from threading import Thread
import json
import time
import queue
import cachetools
import math
from tkinter import filedialog
import datetime
import atexit



status_text = None
field_value_texts = {}
field_parameters = []
channel_textboxes = {}
data = {}
signal_value_counters = {}
counter_labels = {}
previous_values = {}
bus_instances = []
filtered_database = []
root = None
error_counter_text = None
last_receive_time = time.time()

message_counters = {}
decoded_info = {}

can_data_buffer = []
can_data_queue = queue.Queue(maxsize=10000)
channel_configurations = []
received_messages = {}
error_counter = 0
global_msg_cnt = 0
time_sleep_gui = 0.5  # GUI delay in seconds



def load_json():
    # Set current directory
    current_directory = os.getcwd() + '\\Configuration files'
    print('directory_JSON-files:',current_directory)

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
            data = json.load(json_file)
        return data
    else:
        print('No JSON-file found.')
        return None



def load_data_from_dbc(filename, cache):
    # Add caching before loading data from dbc
    if filename in cache:
        return cache[filename]
    else:
        data = load_data_from_file(filename)
        cache[filename] = data
        return data



def load_data_from_file(filename):
    return f"Data from file: {filename}"



def database_list(databases, dbc_filenames, dbc_file_list):
    global database
    for dbc_filename in dbc_filenames:
        if dbc_filename and os.path.exists(dbc_filename):
            db = cantools.database.load_file(dbc_filename)
            databases.append(db)
            print(f"Loaded DBC file: {dbc_filename}")
            dbc_file_list.append(dbc_filename)
        else:
            print(f"Warning: DBC file not found or path is empty: {dbc_filename}")
    return dbc_file_list, databases




def setup_can_buses(channel_configurations):
    # Iterate over the channel configurations in the JSON
    for i in range(1, 20):
        interface_key = f"Interface{i}"
        channel_key = f"Channel{i}"
        bitrate_key = f"Bitrate{i}"

        interface = data.get(interface_key)
        channel = data.get(channel_key)
        bitrate = data.get(bitrate_key)

        # Check if the configuration is empty (not configured)
        if interface and channel and bitrate:
            channel_configurations.append({"interface": interface, "channel": channel, "bitrate": bitrate})

    bus_instances = []

    for config in channel_configurations:
        bus = can.interface.Bus(channel=config["channel"], bustype=config["interface"], bitrate=config["bitrate"])
        bus_instances.append(bus)

    return bus_instances



def filter_databases(databases):
    # Make copy of databases
    filtered_database = databases

    # Filter database (only save needed messages)
    for h in filtered_database:
        messages_to_remove = []
        for message in h.messages:
            signals_to_remove = []
            for signal in message.signals:
                if signal.name not in field_parameters:
                    signals_to_remove.append(signal)

            for signal in signals_to_remove:
                message.signals.remove(signal)

            # Mark message to be deleted
            if not message.signals:
                messages_to_remove.append(message)

        # Delete marked messages out of database
        for message in messages_to_remove:
            h.messages.remove(message)

    # Delete database objects
    filtered_database = [h for h in filtered_database if h.messages]

    return filtered_database




def put_min_max_in_dict():
    # Put min and max in dictionary
    global min_max_values
    min_max_values = {}
    for field_param_data in data.get("Field_parameters", []):
        key = list(field_param_data.keys())
        Field = key[0]


        value = list(field_param_data.values())
        value = value[0]

        field_parameter_JSON = value['value']

        min_value = value['min']
        if min_value == '' or None:
            min_value = float("-inf")

        max_value = value['max']
        if max_value == '' or None:
            max_value = float("inf")

        min_max_values[field_parameter_JSON] = (min_value, max_value)

    return min_max_values




def create_gui():
    global status_text, field_value_texts, field_parameters, data, signal_value_counters, counter_labels,previous_values, bus_instances, filtered_database, root, error_counter_text, message_names_field_parameters, channel_textboxes


    root = tk.Tk()
    root.title("Display")
    root.state('zoomed')

    signal_timers = {field_parameter: None for field_parameter in field_parameters}

    status_label = tk.Label(root, text="Incoming messages:")
    status_label.grid(row=0, column=0)

    status_text = tk.Text(root, height=1, width=20, state="disabled")
    status_text.grid(row=0, column=1)

    error_counter_label = tk.Label(root, text="Error cnt:")
    error_counter_label.grid(row=0, column=2)

    error_counter_text = tk.Label(root, height=1, width=5)
    error_counter_text.grid(row=0, column=3)
    error_counter_text.config(text="0")

    row1 = 1
    row2 = 0
    row3 = 0

    counter = 0

    for i, (field_parameter, message_name) in enumerate(zip(field_parameters, message_names_field_parameters), start=1):
        message_counters[field_parameter] = 0
        previous_values[field_parameter] = None
        decoded_info[field_parameter] = "N/A"

        signal_value_counters[field_parameter] = 0

        if i >= 74:
            value_label = tk.Label(root, text=message_name + ' :: ' + field_parameter + ":")
            value_label.grid(row=row3, column=12)
            value_text = tk.Text(root, height=1, width=20)
            value_text.grid(row=row3, column=13)
            field_value_texts[field_parameter] = value_text

            value_text.insert("1.0", "Not found in dbc")
            value_text.config(state="disabled")

            # Make GUI elements for counters
            counter_label = tk.Label(root, text='Cnt:')
            counter_label.grid(row=row3, column=14)
            counter_text = tk.Label(root, height=1, width=5, state="disabled")
            counter_text.grid(row=row3, column=15)

            counter_text.config(text="0")
            counter_labels[field_parameter] = counter_text

            channel_label = tk.Label(root, text="Ch:")
            channel_label.grid(row=row3, column=16)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textbox = tk.Label(root, height=1, width=2, state="disabled", text= '-')
            channel_textbox.grid(row=row3, column=17)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textboxes[field_parameter] = channel_textbox  # Voeg het tekstvak toe aan de dictionary

            row3 += 1

        if i >= 37 and i < 74:
            value_label = tk.Label(root, text=message_name + ' :: ' + field_parameter + ":")
            value_label.grid(row=row2, column=6)
            value_text = tk.Text(root, height=1, width=20)
            value_text.grid(row=row2, column=7)
            field_value_texts[field_parameter] = value_text

            value_text.insert("1.0", "Not found in dbc")
            value_text.config(state="disabled")

            # Make GUI elements for counters
            counter_label = tk.Label(root, text='Cnt:')
            counter_label.grid(row=row2, column=8)
            counter_text = tk.Label(root, height=1, width=5, state="disabled")
            counter_text.grid(row=row2, column=9)

            counter_text.config(text="0")
            counter_labels[field_parameter] = counter_text

            channel_label = tk.Label(root, text="Ch:")
            channel_label.grid(row=row2, column=10)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textbox = tk.Label(root, height=1, width=2, state="disabled", text= '-')
            channel_textbox.grid(row=row2, column=11)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textboxes[field_parameter] = channel_textbox  # Voeg het tekstvak toe aan de dictionary

            row2 += 1

        elif i < 37:
            value_label = tk.Label(root, text=message_name + ' :: ' + field_parameter + ":")
            value_label.grid(row=row1, column=0)
            value_text = tk.Text(root, height=1, width=20)
            value_text.grid(row=row1, column=1)
            field_value_texts[field_parameter] = value_text

            value_text.insert("1.0", "Not found in dbc")
            value_text.config(state="disabled")

            # Make GUI elements for counters
            counter_label = tk.Label(root, text='Cnt:')
            counter_label.grid(row=row1, column=2)

            counter_text = tk.Label(root, height=1, width=5, state="disabled")
            counter_text.grid(row=row1, column=3)
            counter_text.config(text="0")
            counter_labels[field_parameter] = counter_text

            channel_label = tk.Label(root, text="Ch:")
            channel_label.grid(row=row1, column=4)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textbox = tk.Label(root, height=1, width=2, state="disabled", text= '-')
            channel_textbox.grid(row=row1, column=5)  # Aangepaste kolom om ruimte te maken voor het kanaal

            channel_textboxes[field_parameter] = channel_textbox  # Voeg het tekstvak toe aan de dictionary

            row1 += 1

        counter += 1

        if value_text.get("1.0", "end").strip() == "Not found in dbc":
            value_text.tag_add("bold", "1.0", "end")
            value_text.tag_config("bold", font=("Helvetica", 10, "bold"))




def init():
    global start_time_logger, log_file, status_text, field_value_texts, field_parameters, data, signal_value_counters, counter_labels,previous_values, bus_instances, filtered_database, root, error_counter_text, message_names_field_parameters, error_counter

    # Call function load_json()
    data = load_json()

    # Caching
    cache = cachetools.LRUCache(maxsize=500)

    # Use function to load data
    data1 = load_data_from_dbc("file1.dbc", cache)
    data2 = load_data_from_dbc("file2.dbc", cache)

    cached_data1 = load_data_from_dbc("file1.dbc", cache)
    cached_data2 = load_data_from_dbc("file2.dbc", cache)

    # Get paths to DBC files from JSON-data
    dbc_filenames = [data.get(f"Locatie Database CAN{i}") for i in range(1, 20) if data.get(f"Locatie Database CAN{i}")]

    # Check if the path to DBC files exists and create a list of loaded databases
    databases = []

    dbc_file_list = []

    # Call function database_list()
    dbc_file_list, databases = database_list(databases, dbc_filenames, dbc_file_list)

    # Call function setup_can_buses()
    bus_instances = setup_can_buses(channel_configurations)

    # Get field_parameters from data JSON-file
    dbc_filename = data.get("Locatie Database CAN")
    field_parameters = [field_data[f"Field{i}"]["value"] for i, field_data in enumerate(data.get("Field_parameters"), start=1)]

    # Get names of signals field_parameters
    message_names_field_parameters = [field_data[f"Field{i}"]["message"] for i, field_data in enumerate(data.get("Field_parameters"), start=1)]

    # Call function filter_databases()
    filtered_database = filter_databases(databases)

    # Call function put_min_max_in_dict()
    put_min_max_in_dict()

    # Call function create_gui()
    create_gui()

    # Create log file path en open file
    log_file_path = create_log_file_path()
    log_file = open(log_file_path, "a")

    # Initialise in log file:
    timestamp = datetime.datetime.now().strftime("%a %b %d %I:%M:%S.%f")[:-3] + datetime.datetime.now().strftime(" %p %Y")
    timestamp = timestamp.replace("AM", "am").replace("PM", "pm")

    log_file.write("date " + f"{timestamp}\n")
    log_file.write("base hex  timestamps absolute\n")
    log_file.write("internal events logged\n")
    log_file.write("// version 9.0.0\n")
    log_file.write("Begin Triggerblock " + f"{timestamp}\n")
    start_time_logger = time.perf_counter()
    log_file.write(f"   0.000000" +" Start of measurement\n")




# Function to update the list of received messages through CAN-interface
def update_list_received_messages(message, dict_recv_msg_cnt):
    #print('\n in function update_list_received_messages(message, dict_recv_msg_cnt)')

    id = message.arbitration_id

    if id not in dict_recv_msg_cnt:
        list_received_messages.append(message)
        dict_recv_msg_cnt[id] = 1

    else:
        # Overwrite message in list
        for message_in_list in list_received_messages: # Loop in list
            index = list_received_messages.index(message_in_list)  # Get index list value
            if message_in_list.arbitration_id == id:   # If messages are the same
                list_received_messages[index] = message  # Overwrite message with new message
                break

        # Update counter
        message_counter = dict_recv_msg_cnt.get(id)
        dict_recv_msg_cnt[id] = message_counter + 1



# Function to format message to put in logger file
def format_message_for_log_file(message, start_time_logger):
    timestamp = time.perf_counter() - start_time_logger
    hex_data = ' '.join([f"{byte:02X}" for byte in message.data])
    message_channel = message.channel + 1
    ID_for_log_file = f'{message.arbitration_id:08X}x'

    return f"{timestamp:.6f} {message_channel}  {ID_for_log_file}       Rx   d {message.dlc} {hex_data}"




# Function to receive can data. This data is put in a list and in a logger file.
def receive_and_process_can_data():
    #print('\n in function receive_and_process_can_data()')
    global list_received_messages, dict_recv_msg_cnt, error_counter, global_msg_cnt
    list_received_messages = []
    dict_recv_msg_cnt = {}
    message_counter = 0
    while True:
        try:
            for bus in bus_instances:

                message = bus.recv()
                global_msg_cnt += 1

                if message.is_error_frame:
                    print('message.is_error_frame')
                    error_counter += 1
                elif message is not None:
                    update_list_received_messages(message, dict_recv_msg_cnt)

                    # Write the CAN message to the log file
                    timestamp = datetime.datetime.now().strftime("%a %b %d %I:%M:%S.%f %p %Y")[:-6].lower()
                    message_for_log_file = format_message_for_log_file(message, start_time_logger)
                    log_file.write(f"   {message_for_log_file} \n")


        # Error handling
        except Exception as e:
            error_counter += 1
            print(f'{e}')
            continue




# Decode CAN-message with database-CAN specified in JSON-file
def decode_can_message(databases, can_message):
    global status_text, field_value_texts, field_parameters, data, signal_value_counters, counter_labels, previous_values, bus_instances, filtered_database, root, error_counter_text, message_names_field_parameters

    try:
        start_time = time.perf_counter()
        if databases is None:
            return None, None

        found_message = None

        for db in databases:
            for message_dbc_file in db.messages:
                  if message_dbc_file.frame_id & 0xff == 0xfe:
                      if (message_dbc_file.frame_id & 0xffffff00) == (can_message.arbitration_id & 0xffffff00):
                        found_message = message_dbc_file
                        break
                  else:
                      if (message_dbc_file.frame_id) == (can_message.arbitration_id):
                        found_message = message_dbc_file
                        break
            if found_message:
                break

        if not found_message:
            return None, None

        decoded_message = db.decode_message(found_message.name, can_message.data)
        name_of_found_message = found_message.name

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        #print('elapsed_time_decode_can_message:', elapsed_time*1000)

    except AttributeError:
        return None

    return decoded_message, name_of_found_message




# Update textbox color based on min-values and max-values
def update_textbox_color(field_parameter, current_value, min_value, max_value):

    start_time = time.time()
    value_text_widget = field_value_texts[field_parameter]

    if current_value is None:
        value_text_widget.config(bg='white')

    elif isinstance(current_value, float or int) is not True:
        value_text_widget.config(bg='white')

    else:
        if current_value < min_value or current_value > max_value:
            value_text_widget.config(bg='red')
        else:
            value_text_widget.config(bg='white')

    end_time = time.time()
    elapsed_time = end_time - start_time
    #print('elapsed_time_utc:', elapsed_time*1000)




# Function to update signal values, channel values and counters in the GUI.
def update_gui_values(decoded_message, name_of_found_message, id, message):
    #print('\n in function update_signal_values(decoded_message, name_of_found_message)')
    global status_text, field_value_texts, field_parameters, data, signal_value_counters, counter_labels, previous_values, bus_instances, filtered_database, root, error_counter_text, message_names_field_parameters

    start_time = time.perf_counter()

    if decoded_message is not None:
        for i, (field_parameter, message_name) in enumerate(zip(field_parameters, message_names_field_parameters), start=1): # Loop over field_parameters in JSON-file
            if field_parameter in decoded_message and (message_name == name_of_found_message or message_name == ''):

                current_value = decoded_message.get(field_parameter)
                value_text_widget = field_value_texts[field_parameter]
                value_text_widget.config(state="normal")
                # Get old value
                old_value = value_text_widget.get("1.0", "end").strip()
                # Compare old value to current value

                if str(current_value) != old_value:
                    # Update value text in gui
                    value_text_widget.delete("1.0", "end")
                    value_text_widget.insert("1.0", str(current_value))
                    # Call function update_textbox_color
                    a = field_parameter
                    update_textbox_color(field_parameter, current_value, *min_max_values.get(field_parameter, (-math.inf, math.inf)))


                # Update channel values
                if field_parameter in channel_textboxes:
                    channel_textbox = channel_textboxes[field_parameter]
                    channel_textbox.config(state="normal")
                    channel_value = message.channel
                    channel_textbox.config(text=channel_value)
                    channel_textbox.config(state="disabled")

                value_text_widget.config(state="disabled")

                if id in dict_recv_msg_cnt:
                    counter_value = dict_recv_msg_cnt[id]
                    # Update counter text in gui
                    counter_labels[field_parameter].config(text=counter_value)
                    previous_values[field_parameter] = decoded_message[field_parameter]


    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    #print('elapsed_time_update_signal_values:', elapsed_time*1000)



# Function to update gui based on can status. If there is data: put textbox in green, else put textbox in red.
def update_can_status(status):

    start_time_update_can_status = time.time()
    #print('\n \n \n dit is error counter:',error_counter)

    # If there is no data, put textbox in white
    if status == 'no data':
        status_text.config(bg='red')
        status_text.delete("1.0", "end")
        status_text.insert("1.0", "")
        status_text.config(state="disabled")

    # If there is data, put textbox in green
    if status == 'data':
        status_text.config(bg='green')
        status_text.delete("1.0", "end")
        status_text.insert("1.0", "")
        status_text.config(state="disabled")

    end_time_update_can_status = time.time()
    elapsed_time_update_can_status = end_time_update_can_status - start_time_update_can_status
    #print('elapsed_time_update_can_status:',elapsed_time_update_can_status)



# Function to refresh the gui
def gui_refresh():
    start_time = time.perf_counter()
    global status_text, field_value_texts, field_parameters, data, signal_value_counters, counter_labels, previous_values, bus_instances, filtered_database, root, error_counter_text, message_names_field_parameters, list_received_messages
    #print('Gui is refreshing...')

    prev_msg_cnt = global_msg_cnt
    constant_msg_cnt_time = 0  # Initialize the timer

    while True:
        d = list_received_messages


        for message in list_received_messages:
            #print('Gui is refreshing-2...')
            h = list_received_messages
            if (message.arbitration_id & 0xFF) < 50:
                decoded, name_of_found_message = decode_can_message(filtered_database, message)
                update_gui_values(decoded, name_of_found_message, message.arbitration_id, message)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        #print('elapsed_gui_refresh:', elapsed_time * 1000)
        error_counter_text.config(text=error_counter)

        # Put status-box in green if it there is data, otherwise if there is no data for 2 seconds --> put textbox in red
        if global_msg_cnt == prev_msg_cnt:
            constant_msg_cnt_time += time_sleep_gui  # Add interval gui_refresh

            if constant_msg_cnt_time >= 2.0:  # Check if global message count has remained the same for 2 seconds
                print('global_msg_cnt has remained constant for 2 seconds.')
                update_can_status('no data')
        else:
            constant_msg_cnt_time = 0  # Reset the timer
            prev_msg_cnt = global_msg_cnt
            update_can_status('data')

        time.sleep(time_sleep_gui)



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



# If program exits, end the logger file
def exit_handler():
    if log_file is not None and not log_file.closed:
        log_file.write("End TriggerBlock\n")
        log_file.close()



# Main function
def main():

    # Call function init()
    init()

    # Multithreading
    can_thread = Thread(target=receive_and_process_can_data)
    can_thread.daemon = True
    can_thread.start()

    gui_thread = Thread(target=gui_refresh)
    gui_thread.daemon = True
    gui_thread.start()

    # Register the exit handler
    atexit.register(exit_handler)

    root.mainloop()



if __name__ == "__main__":
    main()



