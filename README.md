# Steps to setup the Raspberry pi

1.Update the system

sudo apt update
sudo apt upgrade -y

2.Install system dependencies

sudo apt install python3-pyusb -y

3.Create an environment if one doesn’t exist

# Navigate to project directory
cd path/to/project
# Create Virtual environment (replace name below with env name)
python3 -m venv name
# Activate the environment
source name/bin/activate

4.Confirm vendor ID

lsusb
output: Bus 003 Device 003: ID 1313:80fa Thorlabs TSP01
Where, 
Vendor ID: 1313
Product ID: 80fa

5.Save the code inside the project directory

6.Run the script from the command line


# Make sure you are inside the correct project directory and environment
python datalogger_TSP01.py

This code has the following functionality
1.	Can modify the logging interval current set to 5sec
2.	5 reset tries if the sensor fails
3.	Can modify the directory where the data is saved
4.	Creates a subfolder inside the specified directory every day and saves data in separate csv files every hour
