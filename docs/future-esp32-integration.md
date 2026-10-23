# Future ESP32 Integration — Not Implemented

JalSaathi currently does not accept live ESP32 payloads and does not control pumps, fans, valves or other actuators. The UI must continue to show **ESP32 integration planned — not connected** until hardware, authentication, calibration, interlocks and field tests are complete.

For a future authenticated HTTPS adapter, use a per-device credential, unique message ID, UTC timestamp, schema version, raw ADC values separate from calibrated readings, and explicit `source: live`. Validate authorization, replay protection, timestamps, plausible bounds, duplicate messages and calibration metadata before comparing any reading with a crop target.

Example documentation-only payload:

```json
{
  "schemaVersion": "1.0.0",
  "deviceId": "device-issued-id",
  "messageId": "uuid-per-message",
  "timestamp": "2026-10-15T12:00:00.000Z",
  "mode": "live",
  "airTemperatureC": 29.4,
  "soilMoisture": {
    "rawAdc": 2180,
    "calibratedValue": null,
    "metric": "raw_adc",
    "calibrationVersion": null
  }
}
```

No current route accepts this payload. No AI response is a control signal. Future control must require explicit confirmation, authorization, safety policy, device acknowledgement, timeout and physical/manual override.
