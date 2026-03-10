import usb.core
import usb.util
import time
import struct
import csv
from datetime import datetime
import os

# --- USER CONFIGURATION ---
VENDOR_ID = 0x1313
PRODUCT_ID = 0x80fa
LOG_INTERVAL_SECONDS = 5
# Set the base directory where you want to save logs.
# Example: '/home/pi00/sensor_logs'
BASE_LOG_DIR = '/home/pi00/witsensor/ThorlabsSensor_Log' 


def get_sensor():
    """Finds and initializes the USB device."""
    dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if dev is None:
        return None
    
    if dev.is_kernel_driver_active(0):
        try:
            dev.detach_kernel_driver(0)
        except usb.core.USBError as e:
            print(f"Could not detach kernel driver: {e}")
            return None
            
    dev.set_configuration()
    return dev

def attempt_reset(dev):
    """Attempts to reset the USB device multiple times."""
    for i in range(5): # Attempt reset up to 5 times
        print(f"Reset attempt {i+1}/5...")
        try:
            dev.reset()
            time.sleep(2) # Wait for device to re-initialize
            new_dev = get_sensor()
            if new_dev:
                print("Device reset and reconnected successfully.")
                return new_dev
        except Exception as reset_e:
            print(f"Reset attempt failed: {reset_e}")
            time.sleep(2)
    return None

def main():
    """Main function to initialize the sensor and log data."""
    print("Attempting to connect to Thorlabs TSP01 sensor...")
    dev = get_sensor()
    
    if dev is None:
        print("Device not found. Exiting.")
        return

    print("Successfully connected.")

    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]
    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    if not ep_out or not ep_in:
        print("Error: Could not find IN/OUT endpoints.")
        return

    print(f"\nStarting data logging. Base directory: '{BASE_LOG_DIR}'")
    print("Press Ctrl-C to stop.")

    # Commands
    measure_humidity_cmd = bytearray.fromhex('F001000207FEFEF1011BDF05A5' + '00'*19)
    fetch_temp_cmd = bytearray.fromhex('F001000207FEFEF1008DEF02D2' + '00'*19)
    fetch_th1_cmd = bytearray.fromhex('F0020002070EF102007D70EF73' + '00'*19)
    ack_command = bytearray.fromhex('F000000201A9F1' + '00'*25)
    
    try:
        while True:
            try:
                # --- Dynamic File/Folder Logic ---
                now = datetime.now()
                day_folder_path = os.path.join(BASE_LOG_DIR, now.strftime('%Y-%m-%d_TSP01'))
                os.makedirs(day_folder_path, exist_ok=True)
                
                log_filename = f"usb_log_{now.strftime('%Y-%m-%d_%H')}.csv"
                full_path = os.path.join(day_folder_path, log_filename)
                
                file_exists = os.path.exists(full_path)

                with open(full_path, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if not file_exists:
                        writer.writerow(["Timestamp", "Temperature_C", "Humidity_RH", "TH1_Temp_C"])
                    
                    # --- Data Acquisition ---
                    ep_out.write(measure_humidity_cmd)
                    ep_in.read(32, timeout=2000)
                    ep_out.write(ack_command)
                    humidity_data = ep_in.read(32, timeout=2000)
                    humidity = struct.unpack('<f', humidity_data[8:12])[0]

                    ep_out.write(fetch_temp_cmd)
                    ep_in.read(32, timeout=2000)
                    ep_out.write(ack_command)
                    temp_data = ep_in.read(32, timeout=2000)
                    temp_c = struct.unpack('<f', temp_data[8:12])[0]

                    ep_out.write(fetch_th1_cmd)
                    ep_in.read(32, timeout=2000)
                    ep_out.write(ack_command)
                    th1_data = ep_in.read(32, timeout=2000)
                    th1_temp = struct.unpack('<f', th1_data[8:12])[0]
                    
                    timestamp_str = now.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{timestamp_str} -> Temp: {temp_c:.2f}°C, Humidity: {humidity:.2f}%, TH1: {th1_temp:.2f}°C")
                    writer.writerow([timestamp_str, f"{temp_c:.2f}", f"{humidity:.2f}", f"{th1_temp:.2f}"])

            except usb.core.USBError as e:
                if e.errno == 110: # Timeout error
                    print("Read timed out. Attempting to reset the USB device...")
                    dev = attempt_reset(dev)
                    if dev is None:
                        print("Could not recover device after multiple reset attempts. Exiting.")
                        break
                    # Re-find endpoints after successful reset
                    cfg = dev.get_active_configuration()
                    intf = cfg[(0,0)]
                    ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
                    ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
                else:
                    raise e

            time.sleep(LOG_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred during logging: {e}")
    finally:
        usb.util.dispose_resources(dev)
        print("Sensor connection closed.")

if __name__ == "__main__":
    main()