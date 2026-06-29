import serial
import json
import re

# ESP32 COM Port
ser = serial.Serial('COM5', 115200)

data = {}

while True:

    line = ser.readline().decode('utf-8', errors='ignore').strip()

    print(line)

    # Temperature
    if "Temperature" in line:
        data["temperature"] = float(
            re.findall(r"[-+]?\d*\.\d+|\d+", line)[0]
        )

    # Humidity
    elif "Humidity" in line:
        data["humidity"] = float(
            re.findall(r"[-+]?\d*\.\d+|\d+", line)[0]
        )

    # Soil Moisture
    elif "Soil Moisture Raw" in line:
        data["soil"] = int(
            re.findall(r"\d+", line)[0]
        )

    # pH
    elif "Estimated pH" in line:
        data["ph"] = float(
            re.findall(r"[-+]?\d*\.\d+|\d+", line)[0]
        )

    # When all sensor values are received
    if (
        "temperature" in data and
        "humidity" in data and
        "soil" in data and
        "ph" in data
    ):

        try:

            # Read existing JSON
            with open("database/sensor_data.json", "r") as f:
                old_data = json.load(f)

            # Update only live sensor values
            old_data["temperature"] = data["temperature"]
            old_data["humidity"] = data["humidity"]
            old_data["soil"] = data["soil"]
            old_data["ph"] = data["ph"]

            # Save back to JSON
            with open("database/sensor_data.json", "w") as f:
                json.dump(old_data, f, indent=4)

            print("JSON Updated Successfully")

        except Exception as e:
            print("Error:", e)