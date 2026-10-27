
# ESP32 + MPU6050 (GY-521) Wiring

## Pin Connections

| MPU6050 / GY-521 | ESP32 DevKit | Purpose |
|---|---|---|
| VCC | 3V3 | Sensor power |
| GND | GND | Common ground |
| SDA | GPIO 21 | I²C data |
| SCL | GPIO 22 | I²C clock |

These are the documented connections for this project's ESP32 setup. Verify the labels and specifications of your particular breakout board before powering it.

## Before Powering On

1. Disconnect power before changing wires.
2. Verify each pin using the board's labels and pinout.
3. Securely mount the sensor to the motor or test rig.
4. Keep wires away from moving parts and hot surfaces.
5. Confirm that the sensor is detected on I²C address `0x68` for the documented setup.

## Serial Data Format

The Python collector expects one line per reading:

```text
ax_raw,ay_raw,az_raw
```

Example format:

```text
125,-42,16320
```

The example values are illustrative, not measured project results.

## Collector Configuration

The documented configuration uses:

- Baud rate: `115200`
- Accelerometer range assumption: ±2 g
- Raw-to-g conversion: `raw / 16384.0`

If the firmware uses a different accelerometer range or outputs values already scaled to g, the firmware and Python collector must agree on the format and units.

## Firmware

Place the tested ESP32 sketch under:

```text
firmware/esp32_sensor/
```

Document the board selection, required libraries, sensor configuration, and upload procedure before publishing the repository as a fully reproducible hardware project.

## Safety

This prototype is intended for learning and demonstration. Secure the sensor and wiring, and do not use this system as the sole protection against hazardous machinery.
