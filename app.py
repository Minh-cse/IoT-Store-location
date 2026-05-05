from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 5000)

import time
import csv
import json
from datetime import datetime, timezone, timedelta
import counterfit_shims_serial
import pynmea2
import paho.mqtt.client as mqtt

# --- HiveMQ config ---
HIVEMQ_HOST = "103ac9061a92450aad5099a849246ddd.s1.eu.hivemq.cloud"   
HIVEMQ_PORT = 8883                        
HIVEMQ_USERNAME = "IoT_GPS"
HIVEMQ_PASSWORD = "1234567890Vgu"
TOPIC = "gps/location"

GPS_TOLORANCE = 0.00009

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

# --- Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ")
    else:
        print(f"Connection failed, code: {rc}")

def on_publish(client, userdata, mid):
    print(f"Message published (mid={mid})")

# --- Setup MQTT client ---
client = mqtt.Client(client_id="gps-tracker-01", protocol=mqtt.MQTTv311)
client.username_pw_set(HIVEMQ_USERNAME, HIVEMQ_PASSWORD)

# TLS
client.tls_set()

client.on_connect = on_connect
client.on_publish = on_publish

print("Connecting to HiveMQ...")
client.connect(HIVEMQ_HOST, HIVEMQ_PORT, keepalive=60)
client.loop_start()

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
            client.publish(TOPIC, json.dumps(payload), qos=1)
    except pynmea2.ParseError:
        pass 

# --- Main loop ---
while True:
    line = serial.readline().decode('utf-8')
    while len(line) > 0:
        send_gps_data(line)
        line = serial.readline().decode('utf-8')
    time.sleep(10)