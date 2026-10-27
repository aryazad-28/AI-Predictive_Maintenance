
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "aiml-predictive-maintenance-demo/sensor"


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)
        print(f"Listening on topic: {TOPIC}")
    else:
        print(f"Connection failed: {reason_code}")


def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8", errors="replace")
    print(f"Received sensor data: {payload}")


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="aiml-pm-python-receiver",
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")
client.connect(BROKER, PORT, keepalive=60)
client.loop_forever()
