
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import math
import paho.mqtt.client as mqtt

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "live_sensor_data.csv"

# Must match the topic in your Wokwi ESP32 firmware
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "aiml-predictive-maintenance-demo/sensor"
SAMPLE_INTERVAL_SECONDS = 0.01  # Nominal 100 Hz sampling
reading_count = 0
batch_count = 0
invalid_count = 0

csv_file = None
csv_writer = None


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker!")
        client.subscribe(TOPIC)
        print(f"Subscribed to: {TOPIC}")
    else:
        print(f"MQTT connection failed: {reason_code}")


def on_message(client, userdata, message):
    global reading_count, batch_count, invalid_count

    payload = message.payload.decode("utf-8", errors="replace").strip()

    # One MQTT message contains multiple readings separated by semicolons.
    items = payload.split(";")
    saved_in_batch = 0

    for index, item in enumerate(items):
        try:
            values = [float(value) for value in item.split(",")]

            if len(values) != 3:
                raise ValueError("Expected three axis values")

            ax, ay, az = values

            if not all(math.isfinite(value) for value in values):
                raise ValueError("Sensor values must be finite numbers")

        except ValueError:
            invalid_count += 1
            print(f"Skipping invalid reading: {item}")
            continue

        # Record the time Python received this reading.
        received_at = datetime.now(timezone.utc).isoformat()

        csv_writer.writerow([
            reading_count * SAMPLE_INTERVAL_SECONDS,
            received_at,
            time.time(),
            batch_count + 1,
            index + 1,
            ax,
            ay,
            az,
        ])

        reading_count += 1
        saved_in_batch += 1

    if saved_in_batch > 0:
        batch_count += 1

        # Ensure newly collected readings reach the CSV immediately.
        csv_file.flush()

        print(
            f"Batch received: {saved_in_batch} readings | "
            f"Total saved: {reading_count}"
        )


def main():
    global csv_file, csv_writer

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Append mode preserves readings from previous runs.
    csv_file = open(
        OUTPUT_PATH,
        "a",
        newline="",
        encoding="utf-8",
    )

    csv_writer = csv.writer(csv_file)

    # Write the column names only when creating a new or empty file.
    if OUTPUT_PATH.stat().st_size == 0:
        csv_writer.writerow([
            "time_seconds",
          "received_at_utc",
          "received_timestamp",
          "batch_number",
          "reading_number_in_batch",
          "ax_g",
          "ay_g",
          "az_g",
        ])
        csv_file.flush()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="aiml-pm-live-collector"
    )

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print("Starting live sensor collector...")
        print(f"CSV output: {OUTPUT_PATH}")
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_forever()

    except KeyboardInterrupt:
        print("\nCollector stopped by user.")

    except Exception as error:
        print(f"Collector error: {error}")

    finally:
        client.disconnect()
        client.loop_stop()

        if csv_file is not None:
            csv_file.close()

        print(f"Total valid readings saved: {reading_count}")
        print(f"Invalid readings skipped: {invalid_count}")
        print(f"CSV location: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
