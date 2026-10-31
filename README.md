# Smart Manufacturing Cloud Ecosystem

A beginner-friendly mini project demonstrating how a manufacturing company can connect IoT devices, production systems and analytics applications through cloud services.

## Features

- Three simulated factory machines: cutting, drilling and packaging.
- Simulated temperature, vibration, energy and production telemetry.
- Live dashboard refresh every 3 seconds.
- Machine status: Running, Idle or Warning.
- Automatic threshold-based alerts.
- Alert acknowledgement.
- Production and energy analytics charts.
- Local SQLite database (no database installation required).
- AWS IoT Core integration configuration scaffold for the cloud phase.
- MySQL reference schema.

> Important: The local version is fully runnable without an AWS account. AWS IoT Core connectivity is a later configuration step and is not active until you create AWS IoT resources and provide certificates securely.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## Run on Windows

1. Extract the ZIP file.
2. Open the `SmartManufacturing` folder in VS Code.
3. Open Terminal > New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it in PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt terminal and run:

   ```cmd
   .venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```powershell
   python -m pip install -r backend/requirements.txt
   ```

7. Start the server from the project root:

   ```powershell
   python -m uvicorn backend.main:app --reload
   ```

8. Open this address in your browser:

   http://127.0.0.1:8000

9. API documentation is available at:

   http://127.0.0.1:8000/docs

## How to test

- Wait 5–10 seconds for the first machine readings.
- The machine cards should update about every 3 seconds.
- Warning alerts are generated when temperature is 78°C or higher, or vibration is 6.5 mm/s or higher.
- Click Acknowledge on an alert to mark it as handled.
- Data is stored in `database/manufacturing.db`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API health |
| GET | `/api/machines` | Machine list and latest telemetry |
| GET | `/api/summary` | Production and energy KPIs |
| GET | `/api/history/M001` | Recent readings for a machine |
| GET | `/api/analytics` | Aggregated machine metrics |
| GET | `/api/alerts` | Recent alerts |
| POST | `/api/alerts/{id}/acknowledge` | Acknowledge an alert |

## Architecture

Local demo:
`Machine simulator -> FastAPI -> SQLite -> Web dashboard`

Cloud extension:
`IoT devices / simulator -> AWS IoT Core (MQTT) -> cloud processing/storage -> analytics`

Suggested AWS ecosystem mapping:
- AWS IoT Core: secure device connectivity and MQTT message broker.
- AWS IoT Greengrass: edge processing close to equipment (optional).
- AWS IoT SiteWise: industrial equipment data modelling and monitoring (optional).
- Amazon S3: durable object storage for historical exports.
- AWS Glue + Athena: data preparation and SQL analytics on S3 (optional).
- Amazon QuickSight: business intelligence dashboards (optional).
- AWS IAM: identity and access management.

## Safety and project limitations

- All sensor values are simulated; no physical factory equipment is connected.
- Threshold alerts are rule-based demonstrations, not certified industrial safety systems.
- The cloud scaffold is not an active AWS deployment.
- Do not upload AWS certificates, private keys or credentials to GitHub.
- Check AWS pricing and configure budgets before creating billable resources.
