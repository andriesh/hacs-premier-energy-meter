# Premier Energy Meter

A Home Assistant custom integration that submits a manual electricity meter reading and a fresh snapshot from a configured camera to Premier Energy Moldova.

## What It Does

1. Takes a JPEG snapshot from the selected Home Assistant camera.
2. Logs into the Premier Energy portal and submits the reading and photo.
3. Shows a Home Assistant persistent notification and writes the result to the Home Assistant log.

The integration stores its credentials in Home Assistant's encrypted configuration-entry storage. It does not use `.env`, Docker Compose variables, shell commands, OCR, or the mock services.

## HACS Installation

1. Push this repository to GitHub. Before publishing, replace `@YOUR_GITHUB_USERNAME` and the example GitHub URLs in `custom_components/premier_energy_meter/manifest.json`.
2. In Home Assistant, open HACS, then **Integrations**.
3. Open the three-dot menu, select **Custom repositories**, and add your GitHub repository URL with category **Integration**.
4. Search for **Premier Energy Meter** in HACS and install it.
5. Restart Home Assistant.
6. Go to **Settings** -> **Devices & services** -> **Add integration** -> **Premier Energy Meter**.
7. Enter the portal username/password, NLC, and select the camera pointing at your meter.

## Dashboard

After setup, the integration automatically creates a writable **Meter reading** number entity under the Premier Energy Meter device. It also displays a persistent notification confirming that setup completed. Entity IDs can vary, so select this entity from the dashboard editor if its generated ID differs from the example.

Home Assistant does not provide custom integrations with a supported API for creating or modifying a user's Lovelace dashboards. This protects existing dashboard configuration. Add a Manual card using [`examples/dashboard.yaml`](examples/dashboard.yaml), replacing `camera.REPLACE_WITH_YOUR_CAMERA_ENTITY` with the camera entity configured in the integration.

The button calls the `premier_energy_meter.submit_reading` service with the helper's value. Alternatively, call the service from an automation or the Developer Tools -> Actions page:

```yaml
action: premier_energy_meter.submit_reading
data:
  reading: "12345"
```

## Logs And Confirmation

After each request, Home Assistant shows a persistent notification. It also writes success/failure entries under the `custom_components.premier_energy_meter` logger in **Settings** -> **System** -> **Logs**.

## Development Installation

For local testing, copy `custom_components/premier_energy_meter/` to `<Home Assistant config>/custom_components/premier_energy_meter/`, restart Home Assistant, and add the integration through the UI.

## Notes

Premier Energy's portal is an external service; changes to its login form or submission endpoint may require an integration update. Do not commit real account credentials, Home Assistant configuration directories, snapshots, or the `src/` scrape directory.
