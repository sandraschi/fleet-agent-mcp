"""Fritz devices-watch anomaly spike (PyOD-optional).

Purpose: prove PyOD ECOD adds value on top of Fritz heartbeat + rust-devices history,
without bloating fleet-agent-mcp core deps.

Data sources (in priority order):
  1. Real DB: %LOCALAPPDATA%/rust-devices-mcp/devices.db (or --db override)
     - energy_readings(ts, device_ip, vendor, watts, kwh)
     - weather_readings(ts, temp_c, ...)
  2. Synthetic demo (--demo): 7 days hourly server-plug + room-temp with injected spikes.

Detector:
  - Try: from pyod.models.ecod import ECOD (pip install pyod - optional)
  - Fallback: pure-python z-score on watts/temp delta (no deps, always works)

Usage:
  uv run python scripts/devices_anomaly_spike.py --demo
  uv run python scripts/devices_anomaly_spike.py --demo --json-out out.json
  # real DB (when sampler has filled it):
  # --db <path> --device-ip 192.168.0.38 --hours 168

Integration path (if spike proves useful):
  - New Fritz tool: devices_anomaly_scan(device_ip, hours) in src/fleet_agent/mcp/tools/surveil.py
  - Called from heartbeat_wake idle path + morning_brief workflow
  - Publishes to Intel Hub via intel_reports_publish + aiwatcher_push_event on urgency >= 8
  - pyod stays optional: pyproject [project.optional-dependencies] anomaly = ["pyod>=2.0"]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path


def default_db_path() -> Path:
    override = os.environ.get("DEVICES_DB", "").strip()
    if override:
        return Path(override)
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        return Path(local) / "rust-devices-mcp" / "devices.db"
    return Path("devices.db")


def load_energy(db: Path, device_ip: str, hours: int, limit: int = 5000) -> list[tuple[int, float]]:
    if not db.is_file():
        return []
    since = int(datetime.now(UTC).timestamp()) - hours * 3600
    try:
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute(
                "SELECT ts, watts FROM energy_readings "
                "WHERE device_ip = ? AND ts >= ? ORDER BY ts ASC LIMIT ?",
                (device_ip, since, limit),
            ).fetchall()
            return [(int(ts), float(w)) for ts, w in rows]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"warn: energy query failed: {exc}", file=sys.stderr)
        return []


def load_weather(db: Path, hours: int, limit: int = 5000) -> list[tuple[int, float]]:
    if not db.is_file():
        return []
    since = int(datetime.now(UTC).timestamp()) - hours * 3600
    try:
        conn = sqlite3.connect(str(db))
        try:
            rows = conn.execute(
                "SELECT ts, temp_c FROM weather_readings "
                "WHERE ts >= ? AND temp_c IS NOT NULL ORDER BY ts ASC LIMIT ?",
                (since, limit),
            ).fetchall()
            return [(int(ts), float(t)) for ts, t in rows]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        print(f"warn: weather query failed: {exc}", file=sys.stderr)
        return []


def synth_demo(days: int = 7) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Server plug (~290W) + bedroom temp (~21.5C) with injected anomalies."""
    rnd = random.Random(42)
    now = int(datetime.now(UTC).timestamp())
    energy: list[tuple[int, float]] = []
    weather: list[tuple[int, float]] = []
    n = days * 24
    for i in range(n):
        ts = now - (n - i) * 3600
        # server plug: 290W baseline, nightly dip, noise
        hour = datetime.fromtimestamp(ts, UTC).hour
        base = 290.0 if 7 <= hour <= 22 else 210.0
        w = base + rnd.gauss(0, 8)
        # injected anomalies: outage drop + overload spike
        if i == n - 30:
            w = 12.0  # plug pulled / outage
        if i == n - 10:
            w = 495.0  # heater + server overload
        energy.append((ts, w))
        # room temp: 21.5C + daily wave + noise
        t = 21.5 + 1.2 * math.sin(2 * math.pi * hour / 24.0) + rnd.gauss(0, 0.25)
        if i == n - 10:
            t = 29.8  # matches overload spike
        if i == n - 50:
            t = 14.0  # window left open in winter
        weather.append((ts, t))
    return energy, weather


def featurize(values: list[float]) -> list[list[float]]:
    """2-D features: [value, abs delta from prev] - catches spikes and level shifts."""
    feats: list[list[float]] = []
    prev = values[0] if values else 0.0
    for v in values:
        feats.append([v, abs(v - prev)])
        prev = v
    return feats


def detect_zscore(
    feats: list[list[float]], contamination: float = 0.05
) -> tuple[list[int], list[float]]:
    """Pure-python fallback: z-score on first column + delta column magnitude."""
    n = len(feats)
    if n < 10:
        return [0] * n, [0.0] * n
    col0 = [f[0] for f in feats]
    mean = sum(col0) / n
    var = sum((x - mean) ** 2 for x in col0) / n
    std = math.sqrt(var) if var > 0 else 1.0
    scores = []
    for v, f in zip(col0, feats, strict=True):
        z = abs(v - mean) / std if std else 0.0
        # boost by normalized delta
        scores.append(z + min(f[1] / (std or 1.0), 5.0) * 0.5)
    k = max(1, int(n * contamination))
    thresh = sorted(scores)[-k]
    labels = [1 if s >= thresh else 0 for s in scores]
    return labels, scores


def detect_ecod(
    feats: list[list[float]], contamination: float = 0.05
) -> tuple[list[int], list[float], str]:
    """Try PyOD ECOD, fall back to z-score. Returns (labels, scores, backend)."""
    try:
        from pyod.models.ecod import ECOD  # type: ignore

        clf = ECOD(contamination=contamination)
        clf.fit(feats)
        labels = [int(x) for x in clf.labels_.tolist()]
        scores = [float(x) for x in clf.decision_scores_.tolist()]
        return labels, scores, "pyod-ecod"
    except ImportError:
        labels, scores = detect_zscore(feats, contamination)
        return labels, scores, "zscore-fallback"
    except Exception as exc:  # PyOD version mismatch etc - never crash spike
        print(f"warn: ECOD failed ({exc}), using fallback", file=sys.stderr)
        labels, scores = detect_zscore(feats, contamination)
        return labels, scores, "zscore-fallback"


def summarize(
    name: str, rows: list[tuple[int, float]], labels: list[int], scores: list[float], unit: str
) -> dict:
    anoms = []
    for (ts, val), lab, score in zip(rows, labels, scores, strict=True):
        if lab == 1:
            anoms.append(
                {
                    "ts": ts,
                    "iso": datetime.fromtimestamp(ts, UTC).isoformat(),
                    "value": round(val, 2),
                    "score": round(score, 3),
                }
            )
    anoms.sort(key=lambda a: a["score"], reverse=True)
    vals = [v for _, v in rows]
    return {
        "series": name,
        "unit": unit,
        "points": len(rows),
        "anomalies": len(anoms),
        "mean": round(sum(vals) / len(vals), 2) if vals else 0,
        "min": round(min(vals), 2) if vals else 0,
        "max": round(max(vals), 2) if vals else 0,
        "top_anomalies": anoms[:10],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Fritz devices-watch PyOD spike")
    ap.add_argument("--db", default=str(default_db_path()))
    ap.add_argument("--device-ip", default="")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--contamination", type=float, default=0.05)
    ap.add_argument("--demo", action="store_true", help="use synthetic data")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    db = Path(args.db)
    if args.demo or not db.is_file():
        if not args.demo and not db.is_file():
            print(f"info: no DB at {db}, using --demo synthetic data", file=sys.stderr)
        energy, weather = synth_demo()
        source = "synthetic-demo"
        device_ip = "demo-server-plug"
    else:
        # pick device: explicit or most-sampled in window
        device_ip = args.device_ip
        if not device_ip:
            try:
                conn = sqlite3.connect(str(db))
                try:
                    row = conn.execute(
                        "SELECT device_ip, COUNT(*) c FROM energy_readings "
                        "WHERE ts >= ? GROUP BY device_ip ORDER BY c DESC LIMIT 1",
                        (int(datetime.now(UTC).timestamp()) - args.hours * 3600,),
                    ).fetchone()
                    device_ip = row[0] if row else ""
                finally:
                    conn.close()
            except sqlite3.Error:
                device_ip = ""
        if not device_ip:
            print("error: no device-ip found, pass --device-ip or use --demo", file=sys.stderr)
            return 2
        energy = load_energy(db, device_ip, args.hours)
        weather = load_weather(db, args.hours)
        source = f"db:{db} device:{device_ip}"
        if not energy and not weather:
            print("warn: DB has no rows in window, falling back to demo", file=sys.stderr)
            energy, weather = synth_demo()
            source = "synthetic-demo (db empty)"

    result: dict = {"source": source, "backend": "", "hours": args.hours}
    backends = set()
    if energy:
        feats = featurize([v for _, v in energy])
        labels, scores, backend = detect_ecod(feats, args.contamination)
        backends.add(backend)
        result["energy"] = summarize("energy:watts", energy, labels, scores, "W")
        result["energy"]["device_ip"] = device_ip
    if weather:
        feats = featurize([v for _, v in weather])
        labels, scores, backend = detect_ecod(feats, args.contamination)
        backends.add(backend)
        result["weather"] = summarize("weather:temp_c", weather, labels, scores, "C")
    result["backend"] = "+".join(sorted(backends)) if backends else "no-data"

    # urgency hint for aiwatcher_push_event: max anomaly score normalized
    total_anoms = result.get("energy", {}).get("anomalies", 0) + result.get("weather", {}).get(
        "anomalies", 0
    )
    result["urgency_hint"] = 8.0 if total_anoms >= 2 else (5.0 if total_anoms == 1 else 2.0)
    result["suggested_action"] = (
        "push to Intel Hub + aiwatcher_push_event" if total_anoms >= 2 else "log only, no push"
    )

    out = json.dumps(result, indent=2)
    print(out)
    if args.json_out:
        Path(args.json_out).write_text(out, encoding="utf-8")
        print(f"wrote {args.json_out}", file=sys.stderr)
    try:
        import pyod  # noqa: F401

        print("pyod: installed", file=sys.stderr)
    except ImportError:
        print(
            "pyod: NOT installed (used fallback) - uv pip install pyod to compare", file=sys.stderr
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
