from __future__ import annotations

import asyncio
import os
import random
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "manufacturing.db"
FRONTEND = ROOT / "frontend"

MACHINES = [
    {"machine_id": "M001", "name": "Cutting Machine", "process": "Cutting"},
    {"machine_id": "M002", "name": "Drilling Machine", "process": "Drilling"},
    {"machine_id": "M003", "name": "Packaging Machine", "process": "Packaging"},
]
simulator_running = True
simulator_thread: threading.Thread | None = None


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                temperature REAL NOT NULL,
                vibration REAL NOT NULL,
                energy_kwh REAL NOT NULL,
                production_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


def make_reading(machine: dict[str, str], index: int) -> dict[str, Any]:
    # Values intentionally vary so the dashboard can demonstrate monitoring.
    temperature = round(random.uniform(48, 83), 1)
    vibration = round(random.uniform(1.0, 7.5), 2)
    energy = round(random.uniform(0.3, 1.8), 2)
    production = random.randint(3, 12)
    status = "Running"
    if temperature >= 78 or vibration >= 6.5:
        status = "Warning"
    elif random.random() < 0.08:
        status = "Idle"

    return {
        "machine_id": machine["machine_id"],
        "temperature": temperature,
        "vibration": vibration,
        "energy_kwh": energy,
        "production_count": production,
        "status": status,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def store_reading(reading: dict[str, Any]):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO readings
            (machine_id, temperature, vibration, energy_kwh, production_count, status, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            reading["machine_id"], reading["temperature"], reading["vibration"],
            reading["energy_kwh"], reading["production_count"], reading["status"],
            reading["recorded_at"]
        ))
        if reading["temperature"] >= 78:
            conn.execute(
                "INSERT INTO alerts (machine_id, severity, message, recorded_at) VALUES (?, ?, ?, ?)",
                (reading["machine_id"], "High", f"High temperature: {reading['temperature']} °C", reading["recorded_at"])
            )
        if reading["vibration"] >= 6.5:
            conn.execute(
                "INSERT INTO alerts (machine_id, severity, message, recorded_at) VALUES (?, ?, ?, ?)",
                (reading["machine_id"], "Medium", f"High vibration: {reading['vibration']} mm/s", reading["recorded_at"])
            )
        conn.commit()


def simulator_loop():
    while simulator_running:
        for i, machine in enumerate(MACHINES):
            reading = make_reading(machine, i)
            store_reading(reading)
        time.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global simulator_thread, simulator_running
    init_db()
    simulator_running = True
    simulator_thread = threading.Thread(target=simulator_loop, daemon=True)
    simulator_thread.start()
    yield
    simulator_running = False
    if simulator_thread:
        simulator_thread.join(timeout=2)


app = FastAPI(
    title="Smart Manufacturing Cloud Ecosystem",
    description="IoT machine monitoring, production analytics and cloud-ready integration demo.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MachineCommand(BaseModel):
    status: str


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Smart Manufacturing API"}


@app.get("/api/machines")
def get_machines():
    results = []
    with connect_db() as conn:
        for machine in MACHINES:
            latest = conn.execute(
                "SELECT * FROM readings WHERE machine_id = ? ORDER BY id DESC LIMIT 1",
                (machine["machine_id"],)
            ).fetchone()
            item = dict(machine)
            item["latest"] = dict(latest) if latest else None
            results.append(item)
    return results


@app.get("/api/summary")
def get_summary():
    with connect_db() as conn:
        totals = conn.execute("""
            SELECT COALESCE(SUM(production_count), 0) AS production,
                   COALESCE(ROUND(SUM(energy_kwh), 2), 0) AS energy,
                   COUNT(*) AS readings
            FROM readings
            WHERE recorded_at >= datetime('now', '-24 hours')
        """).fetchone()
        warning_count = conn.execute(
            "SELECT COUNT(*) AS count FROM readings WHERE status = 'Warning' AND id IN (SELECT MAX(id) FROM readings GROUP BY machine_id)"
        ).fetchone()["count"]
        alert_count = conn.execute(
            "SELECT COUNT(*) AS count FROM alerts WHERE acknowledged = 0"
        ).fetchone()["count"]
    return {
        "production_24h": totals["production"],
        "energy_24h": totals["energy"],
        "readings_24h": totals["readings"],
        "machines_in_warning": warning_count,
        "open_alerts": alert_count,
    }


@app.get("/api/history/{machine_id}")
def get_history(machine_id: str, limit: int = 20):
    if machine_id not in [m["machine_id"] for m in MACHINES]:
        raise HTTPException(status_code=404, detail="Machine not found")
    limit = max(1, min(limit, 100))
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT * FROM readings WHERE machine_id = ? ORDER BY id DESC LIMIT ?",
            (machine_id, limit)
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


@app.get("/api/alerts")
def get_alerts():
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT 30"
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int):
    with connect_db() as conn:
        cur = conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": "Alert acknowledged"}


@app.get("/api/analytics")
def analytics():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT machine_id,
                   SUM(production_count) AS production,
                   ROUND(AVG(temperature), 1) AS avg_temperature,
                   ROUND(AVG(vibration), 2) AS avg_vibration,
                   ROUND(SUM(energy_kwh), 2) AS energy
            FROM readings
            WHERE recorded_at >= datetime('now', '-24 hours')
            GROUP BY machine_id
        """).fetchall()
    return [dict(row) for row in rows]


@app.get("/")
def dashboard():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
