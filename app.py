from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 5000)

import time
import csv
import json
from datetime import datetime, timezone, timedelta
import counterfit_shims_serial
import pynmea2
from azure.iot.device import IoTHubDeviceClient, Message

# --- Each truck has its own port and connection string ---
DEVICES = [
    {
        "id": "truck_01",
        "port": "/dev/ttyAMA0",
        "connection_string": "<connection_string_for_truck_01>"
    },
    {
        "id": "truck_02",
        "port": "/dev/ttyAMA1",
        "connection_string": "<connection_string_for_truck_02>"
    },
]

GPS_TOLERANCE = 0.00009
tz_vn = timezone(timedelta(hours=7))

def method_handler(method_request):
    print(f'Direct method received: {method_request.name}')
    
    if method_request.name == 'arrived':
        print('Truck arrived!')
    elif method_request.name == 'in_transit':
        print('Truck is in transit')
    
    response = MethodResponse.create_from_method_request(method_request, status=200)
    device_client.send_method_response(response)

device_client.on_method_request_received = method_handler

# --- Load warehouses ---
def load_warehouse(filepath):
    warehouse = []
    with open(filepath, newline='', encoding='utf-8') as f:
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

# --- Check if GPS is near a warehouse ---
def check_warehouse(lat, lon):
    for wh in warehouse:
        if abs(lat - wh['latitude']) <= GPS_TOLERANCE and abs(lon - wh['longitude']) <= GPS_TOLERANCE:
            return wh
    return None

# --- Send GPS data to Azure ---
def send_gps_data(line, device_client, device_id):
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
                "device_id": device_id,
                "timestamp": timestamp,
                "gps": {
                    "lat": lat,
                    "lon": lon
                }
            }

            matched = check_warehouse(lat, lon)
            if matched:
                payload["warehouse"] = {
                    "warehouse": matched["warehouse"],
                    "lat": matched["latitude"],
                    "lon": matched["longitude"],
                }
                print(f"[{device_id}] At {matched['warehouse']} | Lat: {lat:.6f}, Lon: {lon:.6f} | {timestamp}")
            else:
                print(f"[{device_id}] Sending telemetry | Lat: {lat:.6f}, Lon: {lon:.6f} | {timestamp}")

            message = Message(json.dumps(payload))
            device_client.send_message(message)
    except pynmea2.ParseError:
        pass

# --- Connect all devices ---
print("Connecting devices...")
for device in DEVICES:
    device["serial"] = counterfit_shims_serial.Serial(device["port"])
    device["client"] = IoTHubDeviceClient.create_from_connection_string(device["connection_string"])
    device["client"].connect()
    print(f"Connected: {device['id']} on {device['port']}")

print("All devices connected!")

# --- Main loop ---
while True:
    for device in DEVICES:
        line = device["serial"].readline().decode('utf-8')
        while len(line) > 0:
            send_gps_data(line, device["client"], device["id"])
            line = device["serial"].readline().decode('utf-8')
    time.sleep(60)
