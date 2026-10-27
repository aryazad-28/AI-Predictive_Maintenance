
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import serial

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "live_sensor_data.csv"

PORT = "COM5"
BAUD_RATE = 115200

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0
    mode = "a" if file_exists else "w"

    print(f"Connecting to ESP32 on {PORT}...")

    with serial.Serial(PORT, BAUD_RATE, timeout=1) as esp32:
        time.sleep(2)
        esp32.reset_input_buffer()

        with open(OUTPUT_PATH, mode, newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow([
                    "time_seconds",
                    "received_at_utc",
                    "received_timestamp",
                    "batch_number",
                    "reading_number_in_batch",
                    "ax_g",
                    "ay_g",
                    "az_g",
                ])

            count = 0
            start_time = time.time()
            print("Collecting sensor readings. Press Ctrl+C to stop.")

            try:
                while True:
                    line = esp32.readline().decode(
                        "utf-8", errors="ignore"
                    ).strip()

                    if not line:
                        continue

                    parts = line.split(",")

                    if len(parts) != 3:
                        continue

                    try:
                        ax_raw, ay_raw, az_raw = map(float, parts)
                    except ValueError:
                        continue

                    # Convert raw MPU6050 readings to g.
                    # This assumes the default +/-2g range.
                    ax_g = ax_raw / 16384.0
                    ay_g = ay_raw / 16384.0
                    az_g = az_raw / 16384.0

                    received = time.time()
                    count += 1

                    
                    writer.writerow([
                        received - start_time,
                        datetime.now(timezone.utc).isoformat(),
                        received,
                        1,
                        count,
                        ax_g,
                        ay_g,
                        az_g,
                    ])


                    if count % 100 == 0:
                        file.flush()
                        print(
                            f"Saved {count} readings | "
                            f"Latest: {ax_g:.3f}, "
                            f"{ay_g:.3f}, {az_g:.3f} g"
                        )

            except KeyboardInterrupt:
                print("\nCollection stopped.")

            finally:
                file.flush()
                print(f"Saved {count} readings to:")
                print(OUTPUT_PATH)


if __name__ == "__main__":
    main()

