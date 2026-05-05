from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 5000)

import time
import counterfit_shims_serial
import pynmea2
import json
import paho.mqtt.client as mqtt

# --- HiveMQ config ---
HIVEMQ_HOST = "103ac9061a92450aad5099a849246ddd.s1.eu.hivemq.cloud"   
HIVEMQ_PORT = 8883                          
HIVEMQ_USERNAME = "IoT_GPS"
HIVEMQ_PASSWORD = "1234567890Vgu"
TOPIC = "gps/location"

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

# --- Gửi GPS ---
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
            message_json = {"gps": {"lat": lat, "lon": lon}}
            print("Sending telemetry", message_json)
            client.publish(TOPIC, json.dumps(message_json), qos=1)
    except pynmea2.ParseError:
        pass 

# --- Main loop ---
while True:
    line = serial.readline().decode('utf-8')
    while len(line) > 0:
        send_gps_data(line)
        line = serial.readline().decode('utf-8')
    time.sleep(10)