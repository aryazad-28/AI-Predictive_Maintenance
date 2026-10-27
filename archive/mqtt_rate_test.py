
import time
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "aiml-predictive-maintenance-demo/sensor"

message_count = 0
reading_count = 0
invalid_count = 0
start_time = None
last_report_time = None


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)
        print(f"Listening on topic: {TOPIC}")
        print("Measuring incoming sensor batches...")
    else:
        print(f"Connection failed: {reason_code}")


def on_message(client, userdata, message):
    global message_count, reading_count, invalid_count
    global start_time, last_report_time

    now = time.time()

    if start_time is None:
        start_time = now
        last_report_time = now

    payload = message.payload.decode("utf-8", errors="replace").strip()

    # One MQTT message contains multiple readings.
    # Semicolons separate readings; commas separate axes.
    batch_readings = []

    for item in payload.split(";"):
        try:
            values = [float(value) for value in item.split(",")]

            if len(values) != 3:
                raise ValueError("Expected exactly 3 axis values")

            batch_readings.append(values)

        except ValueError:
            invalid_count += 1

    if not batch_readings:
        print(f"Invalid batch received: {payload}")
        return

    message_count += 1
    reading_count += len(batch_readings)

    latest = batch_readings[-1]

    if now - last_report_time >= 5:
        elapsed = now - start_time

        print("\n--- MQTT Sensor Test ---")
        print(f"Valid MQTT batches: {message_count}")
        print(f"Valid sensor readings: {reading_count}")
        print(f"Invalid readings: {invalid_count}")
        print(f"Elapsed time: {elapsed:.2f} seconds")

        if elapsed > 0:
            print(
                "Average reading rate: "
                f"{reading_count / elapsed:.2f} readings/second"
            )
            print(
                "Average batch rate: "
                f"{message_count / elapsed:.2f} messages/second"
            )

        print(
            f"Latest reading: ax={latest[0]:.4f}, "
            f"ay={latest[1]:.4f}, az={latest[2]:.4f}"
        )

        last_report_time = now


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="aiml-pm-python-batch-test"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")
client.connect(BROKER, PORT, keepalive=60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nTest stopped by user.")

    if start_time is not None:
        elapsed = time.time() - start_time

        print("\n--- Final Results ---")
        print(f"Valid MQTT batches: {message_count}")
        print(f"Valid sensor readings: {reading_count}")
        print(f"Invalid readings: {invalid_count}")
        print(f"Elapsed time: {elapsed:.2f} seconds")

        if elapsed > 0:
            print(
                "Average reading rate: "
                f"{reading_count / elapsed:.2f} readings/second"
            )
finally:
    client.disconnect()
    client.loop_stop()
