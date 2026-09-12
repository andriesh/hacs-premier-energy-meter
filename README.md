# Premier Energy Meter

Premier Energy Meter is a Home Assistant integration for submitting an electricity meter reading to Premier Energy Moldova. It sends the manually entered reading together with a fresh JPEG snapshot from your meter camera.

## Features

- Captures a current image from the configured camera.
- Submits the image and manual reading to the Premier Energy portal.
- Creates an admin-only **Premier Energy Meter** dashboard with the live camera feed, reading input, and submit button.
- Shows a Home Assistant notification and log entry after every submission.

## Install With HACS

Before installing, configure a Generic Camera integration in Home Assistant with the live video stream from the electricity meter. Verify that its live view works and that the meter digits are clearly visible.

1. Open **HACS** in Home Assistant and select **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository's GitHub URL with category **Integration**.
4. Search for **Premier Energy Meter** and select **Download**.
5. Restart Home Assistant.
6. Go to **Settings** -> **Devices & services** -> **Add integration**.
7. Select **Premier Energy Meter**.
8. Enter your Premier Energy username, password, NLC, and select the preconfigured Generic Camera that faces your electricity meter.

## Use The Dashboard

After setup, open **Premier Energy Meter** from the sidebar. The dashboard is available only to Home Assistant administrators.

1. Confirm that the live camera image shows the meter.
2. Enter the reading in **Meter reading**.
3. Select **Submit reading**.

The integration creates the dashboard only when `/premier-energy-meter` does not already exist. It does not modify any other dashboard.

## Repeat Submissions

The integration does not impose a submission limit. Premier Energy may reject, ignore, or restrict repeated readings according to the billing period and its portal rules. Submit only after checking the displayed reading and notification result; do not retry automatically or submit the same reading repeatedly unless Premier Energy instructs you to do so.

## Submit From An Automation

Call the `premier_energy_meter.submit_reading` action and provide a digits-only reading:

```yaml
action: premier_energy_meter.submit_reading
data:
  reading: "12345"
```

When a single Premier Energy Meter entry is configured, `reading` may be omitted and the integration uses the value shown in its **Meter reading** entity.

## Check Submission Status

Home Assistant shows a persistent notification after each attempt. For technical details, open **Settings** -> **System** -> **Logs** and look for `custom_components.premier_energy_meter`.

## Update

1. Open **HACS** -> **Integrations**.
2. Select **Premier Energy Meter**.
3. Select **Update** or **Redownload**.
4. Restart Home Assistant.

Your configured credentials and camera selection remain in place after an update.

## Releases

Each commit pushed to the `main` branch runs validation, full-history secret scanning, and Python static security analysis. A failed security check prevents a GitHub release. Successful runs create a GitHub prerelease tag in the form `v<manifest-version>-build.<run-number>`, for example `v0.1.0-build.42`. Update the `version` in `custom_components/premier_energy_meter/manifest.json` before a release when the integration version changes.

## Remove

1. Go to **Settings** -> **Devices & services**.
2. Select **Premier Energy Meter** and choose **Delete**.
3. In HACS, open **Premier Energy Meter** and select **Remove**.

Removing the integration does not delete snapshots already stored in Home Assistant's `www` directory or the dashboard created during setup.
