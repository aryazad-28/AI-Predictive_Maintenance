
# Testing and Validation Checklist

Use this checklist before a project demonstration. Record actual results, timestamps, and evidence. Do not mark tests as passed until they have been performed.

## A. Hardware and Collection

- [ ] ESP32 is detected on the configured serial port.
- [ ] Serial output contains three numeric comma-separated values per reading.
- [ ] The collector creates the expected CSV header and appends rows.
- [ ] `received_timestamp` increases with each received reading.
- [ ] The sensor scale and units match the collector's conversion.
- [ ] Stopping the collector or disconnecting the sensor is noticed.

## B. Healthy Baseline Learning

- [ ] The motor is verified healthy before learning begins.
- [ ] The learning interval is bounded to the intended 30 seconds.
- [ ] Only readings from the learning interval are used for baseline creation.
- [ ] Enough complete windows are available.
- [ ] The baseline JSON contains the expected machine ID, version, window size, feature names, and statistics.
- [ ] The baseline remains pending review until explicitly activated.
- [ ] Learning-period readings do not appear as post-activation anomaly results.

## C. Activation Boundary

- [ ] The registry contains the active baseline version.
- [ ] The active registry record includes `activated_at_utc`.
- [ ] The monitor excludes readings at or before the activation timestamp.
- [ ] The first monitored window contains only post-activation readings.
- [ ] Partial-window behavior at the activation boundary is verified.

## D. Detection and Persistence

- [ ] Known healthy post-activation readings produce the expected comparisons.
- [ ] One anomalous window alone does not trigger a persistent alert.
- [ ] Two anomalous windows in a five-window sequence do not trigger the 3-of-5 alert.
- [ ] Three anomalous windows among the latest five trigger the configured persistent alert.
- [ ] Alert recovery behaves as expected when anomalous windows leave the rolling window.
- [ ] Deviating feature names and values can be inspected.

## E. Live Dashboard

- [ ] The vibration chart advances while readings arrive.
- [ ] The monitoring window count advances as new complete windows become available.
- [ ] The anomaly chart uses the intended time field and units.
- [ ] The latest status, recent-window table, and persistent alert agree.
- [ ] Missing baseline and empty CSV states show clear messages.
- [ ] Stale data or collector disconnection does not appear to be fresh live data.

## Test Evidence

Complete this table using actual test results.

| Test | Condition | Expected result | Observed result | Pass/Fail | Evidence |
|---|---|---|---|---|---|
| 1 | Verified healthy motor | No persistent alert | _Record result_ | _TBD_ | _Log/screenshot_ |
| 2 | One unusual window | No persistent alert | _Record result_ | _TBD_ | _Log/screenshot_ |
| 3 | Three anomalous windows among latest five | Persistent alert | _Record result_ | _TBD_ | _Log/screenshot_ |
| 4 | Collector stopped or sensor disconnected | Clear waiting/error state | _Record result_ | _TBD_ | _Log/screenshot_ |

## Reporting Results

Do not claim accuracy, precision, recall, or an industrial fault-detection rate unless the system has been evaluated against labelled ground-truth data using a documented test method.

A persistent anomaly alert means vibration differs from the learned reference. It does not, by itself, confirm a fault or identify its cause.
