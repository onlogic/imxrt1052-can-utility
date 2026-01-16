"""
Author: OnLogic
For:    Reference Documentation
Title:  I.MX RT1052 Example Python CAN Bus Send, Receive, and Loopback Utility

Description:
    This Python script provides a simple interface for CAN bus communication with the I.MX RT1052 add-on card.
    It allows sending and receiving CAN messages through dual virtual CAN ports for testing.

    For more examples and instructions on how to modify the following code, see:
    https://python-can.readthedocs.io/en/v4.3.0/api.html

    Available bit-rates:
        10     20     50     100    125    250    500    800    1000  Kbits/s

Dependencies:
    1. pyserial:
        pip install pyserial
    2. python-can:
        pip install python-can

Usage:
    1. Using command-line arguments:
       Windows: python imxrt1052_can_utility.py [-h] [-m {send,recv,loopback}] [-b {10,20,50,100,125,250,500,750,1000}]
       Linux:   sudo python3 imxrt1052_can_utility.py [-h] [-m {send,recv,loopback}] [-b {10,20,50,100,125,250,500,750,1000}]

    2. Using regular variables (edit the script):
       Set USE_ARGPARSE to False and modify DEFAULT_MODE and DEFAULT_BITRATE

        IF you want to get rid of command line arguments entirely, remove this:
        "
        if USE_ARGPARSE:
            args     = parse_arguments()
            mode     = args.mode
            bit_rate = args.bit_rate
        else:
        "

Examples:
    Windows:
        python imxrt1052_can_utility.py -m loopback -b 1000
        python imxrt1052_can_utility.py -m send

    Linux:
        sudo python3 imxrt1052_can_utility.py -m loopback -b 1000
        sudo python3 imxrt1052_can_utility.py -m recv

NOTE: 
    If you are switching CAN bauds successively between sessions, 
    and are having difficulty in doing so, attempt resetting the microcontroller:
        1. go to the uart terminal through putty or the like (make sure to do so with sudo privileges in ubuntu)
        2. type in 'reset' into the terminal
        3. wait 10 seconds
    And try again
"""

import serial
from serial.tools import list_ports as system_ports

import can
import sys
import argparse

from datetime import datetime
import time

'''---------------- Global Variables ----------------'''
# Vendor ID and Product ID assigned by MCU vendor
MCU_VID_PID = '353F:A103'

# True for command-line, False to use regular variables in main
USE_ARGPARSE = True  # default to CMD

# Default values (used when USE_ARGPARSE is False)
DEFAULT_MODE     = 'loopback'  # 'send', 'recv', or 'loopback'
DEFAULT_BITRATE  = 1000        # baud in kbps
valid_bit_rates  = [10, 20, 50, 100, 125, 250, 500, 750, 1000]
'''--------------------------------------------------'''


def inc_dec_data_string(number, is_increment, low=0, high=9):
    """Generate oscillating data string for debugging."""
    if number == low:
        is_increment = True
    elif number == high:
        is_increment = False

    if is_increment:
        number += 1
    else:
        number -= 1

    return number, is_increment, f'hello_{number}'


def configure_can(port, interface, mode, baud):
    """CAN interface issued to MCU via command line."""
    port.write(f'set can-mode {interface} {mode}\r\n'.encode())
    time.sleep(0.1)
    port.write(f'set can-baudrate {interface} {baud}\r\n'.encode())
    time.sleep(0.1)
    print(port.read(port.inWaiting()).decode())


def get_device_port(dev_id, location=None):
    """Scan and return the port of the target device."""
    all_ports = system_ports.comports() 
    for port in sorted(all_ports):
        if dev_id in port.hwid:
            if location and location in port.location:
                print(f'Port: {port}\tPort Location: {port.location}\tHardware ID: {port.hwid}\tDevice: {port.device}')
                print('*'*15)
                return port.device
    return None


def parse_arguments():
    """Receive and parse command-line arguments."""
    parser = argparse.ArgumentParser(description="I.MX RT1052 CAN Bus Loopback Utility")
    parser.add_argument('-m', '--mode', choices=['send', 'recv', 'loopback'],
                        help="send, recv, or loopback: send generated data, continually receive, or test loopback",
                        default=DEFAULT_MODE)
    parser.add_argument('-b', '--bitrate', choices=valid_bit_rates,
                        help=f"CAN bus baudrate in kbps (ranges allowed by slcan: {valid_bit_rates})",
                        type=int, default=DEFAULT_BITRATE)
    return parser.parse_args()


def main():
    """Main, implementation of session logic."""
    if USE_ARGPARSE:
        args     = parse_arguments()
        mode     = args.mode
        bit_rate = args.bitrate
    else:
        mode     = DEFAULT_MODE
        bit_rate = DEFAULT_BITRATE

    if bit_rate not in valid_bit_rates:
        print(f"Error: Invalid bit_rate. Please enter a value from {valid_bit_rates} kbps.")
        sys.exit(1)

    # Get and Management port, main serial port at baud 9600
    # (equivalent to Putty terminal)
    mgmt_port = get_device_port(MCU_VID_PID, ".0")
    
    # Get virtual CAN interface
    can1_port = get_device_port(MCU_VID_PID, ".2")
    can2_port = get_device_port(MCU_VID_PID, ".4")

    if not mgmt_port:
        print("Error: MCU management port not found. Please check configurations and connections.")
        sys.exit(1)

    if mode in ['loopback'] and not (can1_port and can2_port):
        print("Error: CAN ports necessary for loopback not found. Please check configurations and connections.")
        sys.exit(1)
    elif mode in ['send', 'recv'] and not (can1_port and can2_port):
        print("Error: CAN ports necessary for this script. Please check configurations and connections.")
        sys.exit(1)

    port, bus1, bus2 = None, None, None
    try:
        # Open serial terminal 
        port = serial.Serial(mgmt_port)

        # Write NL to the serial terminal
        port.write(b'\r\n')
        time.sleep(0.1)

        # Show terminal content
        port.read(port.inWaiting())

        # Configure virtualized CAN port(s)
        print("Configuring CAN ports...")
        configure_can(port, 'VCAN1', 'slcan', str(bit_rate))
        configure_can(port, 'VCAN2', 'slcan', str(bit_rate))
        print("CAN ports configured.")

        # Init and create bus using slcan interface on selected can_port(s)
        if can1_port:
            bus1 = can.Bus(interface='slcan', channel=can1_port, bitrate=bit_rate*1000)
        if can2_port:
            bus2 = can.Bus(interface='slcan', channel=can2_port, bitrate=bit_rate*1000)

        print(
            f"Starting CAN bus mode: {mode}...\n"
            "Ctrl+C to exit"
        )

        # Variables for example CAN bus generation
        # Can be removed/replaced with custom implementation
        number = 0
        is_increment = True
 
        while True:
            if mode == 'send':
                # Generate data string
                number, is_increment, data = inc_dec_data_string(number, is_increment)

                # Get the current time to add to can frame report
                msg_time = datetime.now().timestamp()

                # Encode as bytes, transmitting in specified frame format
                message = can.Message(timestamp=msg_time, arbitration_id=0x123, is_extended_id=True, data=data.encode('utf-8'))

                # Send message
                bus1.send(message, timeout=0.2)

                # Print with small delay after send attempt
                print(f"Sent: {message}")
                time.sleep(0.1)

            elif mode == 'recv':
                # Poll for input then print if received a msg
                received_msg = bus1.recv()
                print(f"Received: {received_msg}")

            elif mode == 'loopback':
                # Generate data string
                number, is_increment, data = inc_dec_data_string(number, is_increment)

                # Get the current time to add to can frame report
                msg_time = datetime.now().timestamp()

                # Encode as bytes, transmitting in specified frame format
                message = can.Message(timestamp=msg_time, 
                                      arbitration_id=0x123, 
                                      is_extended_id=True, 
                                      data=data.encode('utf-8'))

                print(f"Sent: {message}")
                bus1.send(message, timeout=0.2)

                received_msg = bus2.recv()
                print(f"Received: {received_msg}")

                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nOperation terminated by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        time.sleep(1)

        # close serial port if open
        if port and port.is_open:
            try:
                port.reset_input_buffer()
                port.reset_output_buffer()
                port.close()
            except Exception: 
                pass
        
        # Shut down busses
        if bus1:
            bus1.shutdown()

        if bus2:    	
    	    bus2.shutdown()

if __name__ == '__main__':
    main()
