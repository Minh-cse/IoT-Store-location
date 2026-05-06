from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 5000)

import time
import csv
import json
from datetime import datetime, timezone, timedelta
import counterfit_shims_serial
import pynmea2
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse  # ← thêm MethodResponse

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

# --- Method handler factory --- 
def make_method_handler(client, device_id):
    def method_handler(method_request):
        print(f'[{device_id}] Direct method received: {method_request.name}')
        if method_request.name == 'arrived':
            print(f'[{device_id}] Truck arrived!')
        elif method_request.name == 'in_transit':
            print(f'[{device_id}] Truck is in transit')
        response = MethodResponse.create_from_method_request(method_request, status=200)
        client.send_method_response(response)
    return method_handler

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
    try:
        device["serial"] = counterfit_shims_serial.Serial(device["port"])
        device["client"] = IoTHubDeviceClient.create_from_connection_string(device["connection_string"])
        device["client"].connect()
        device["client"].on_method_request_received = make_method_handler(device["client"], device["id"])
        device["connected"] = True  # ← đánh dấu connected
        print(f"Connected: {device['id']} on {device['port']}")
    except Exception as e:
        device["connected"] = False  # ← đánh dấu failed
        print(f"Failed to connect {device['id']}: {e}")

# --- Main loop ---
while True:
    for device in DEVICES:
        if not device["connected"]:  # ← bỏ qua device lỗi
            continue
        line = device["serial"].readline().decode('utf-8')
        while len(line) > 0:
            send_gps_data(line, device["client"], device["id"])
            line = device["serial"].readline().decode('utf-8')
    time.sleep(30)
