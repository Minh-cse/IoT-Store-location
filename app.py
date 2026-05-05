from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 5000)

import time
import csv
import json
from datetime import datetime, timezone, timedelta
import counterfit_shims_serial
import pynmea2
from azure.iot.device import IoTHubDeviceClient, Message

connection_string = 'string'

serial = counterfit_shims_serial.Serial('/dev/ttyAMA0')

device_client = IoTHubDeviceClient.create_from_connection_string(connection_string)

GPS_TOLORANCE = 0.00009

print('Connecting')
device_client.connect()
print('Connected')

tz_vn = timezone(timedelta(hours=7))

def load_warehouse(filepath):
    warehouse = []
    with open(filepath, newline = '', encoding = 'utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            warehouse.append({
                'warehouse': row['warehouse'],
                'longitude': float(row['longitude']),
                'latitude': float(row['latitude'])
            })
    print(f"Loaded {len(warehouse)} warehouses from {filepath}")
    return warehouse

warehouse = load_warehouse('warehouse.csv')

def check_warehouse(lat, lon):
    for wh in warehouse:
        if abs(lat - wh['latitude']) <= GPS_TOLORANCE and abs(lon - wh['longitude']) <= GPS_TOLORANCE:
            return wh
    return None

# --- Serial ---
serial = counterfit_shims_serial.Serial('/dev/ttyAMA0')

# --- Send GPS ---
def send_gps_data(line):
    try:
        msg = pynmea2.parse(line)
        if msg.sentence_type == 'GGA':
            lat = pynmea2.dm_to_sd(msg.lat)
            lon = pynmea2.dm_to_sd(msg.lon)
            if msg.lat_dir == 'S':
                lat *= -1
            if msg.lon_dir == 'W':
                lon *= -1
            
            timestamp = datetime.now(tz_vn).strftime("%d/%m/%Y %H:%M:%S") + " UTC+7"

            payload = {
                "timestamp": timestamp,
                "gps": {
                    "lat": lat, 
                    "lon": lon}
            }
            matched = check_warehouse(lat, lon)

            if matched:
                payload["warehouse"] = {
                    "warehouse": matched["warehouse"],
                    "lat": matched["latitude"],
                    "lon": matched["longitude"],
                }
                print(f"Currently at {matched['warehouse']} | Lat: {lat:.6f}, Lon: {lon:.6f} \nTimestamp: {timestamp}") 
            else:
                print("Sending telemetry", payload)
        message = Message(json.dumps(payload))
        device_client.send_message(message)
    except pynmea2.ParseError:
        pass 

# --- Main loop ---
while True:
    line = serial.readline().decode('utf-8')
    while len(line) > 0:
        send_gps_data(line)
        line = serial.readline().decode('utf-8')
    time.sleep(10)