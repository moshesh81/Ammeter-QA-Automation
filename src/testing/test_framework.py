"""Collect current measurements, calculate statistics, and save each test run."""

import json
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from Ammeters.client import request_current_from_ammeter
from src.utils.config import load_config


class AmmeterTestFramework:
    def __init__(self, config_path="config/config.yaml"):
        self.config_path = Path(config_path).resolve()
        self.config = load_config(self.config_path)
        self.settings = self.config["testing"]["sampling"]

        self.count = int(self.settings["measurements_count"])
        self.duration = float(self.settings["total_duration_seconds"])
        self.frequency = float(self.settings["sampling_frequency_hz"])

        if self.count < 1 or self.duration <= 0 or self.frequency <= 0:
            raise ValueError("Count, duration and frequency must be positive")
        if (self.count - 1) / self.frequency > self.duration:
            raise ValueError("Cannot fit this many measurements into the given duration")

        # Resolve the results folder relative to the project root.
        project_root = self.config_path.parent.parent
        output_dir = self.config["result_management"]["output_dir"]
        self.output_dir = project_root / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_test(self, ammeter_type: str) -> dict:
        """Sample one configured ammeter and return an archived report."""
        if ammeter_type not in self.config["ammeters"]:
            raise ValueError(f"Unknown ammeter type: {ammeter_type}")

        device = self.config["ammeters"][ammeter_type]
        started_at = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()  # Not affected by changes to the system clock.
        measurements = []
        errors = []
        timing_warnings = []

        for index in range(self.count):
            # Target times: 0, 1/frequency, 2/frequency, ...
            target_time = start + index / self.frequency
            time.sleep(max(0, target_time - time.monotonic()))

            elapsed = time.monotonic() - start
            if elapsed > self.duration:
                # A slow computer or TCP request can delay the next sample.
                # Keep collecting, but report that the requested timing was missed.
                timing_warnings.append({
                    "sample": index + 1,
                    "elapsed_seconds": round(elapsed, 3),
                    "message": "Sample started after the configured duration",
                })

            try:
                current = request_current_from_ammeter(
                    int(device["port"]), device["command"].encode("utf-8")
                )
                measurements.append({
                    "sample": index + 1,
                    "elapsed_seconds": round(elapsed, 3),
                    "current_amps": current,
                })
            except (OSError, ValueError) as error:
                errors.append({"sample": index + 1, "error": str(error)})

        currents = [item["current_amps"] for item in measurements]
        stats = {
            "mean": statistics.mean(currents) if currents else None,
            "median": statistics.median(currents) if currents else None,
            "std_dev": statistics.stdev(currents) if len(currents) > 1 else None,
            "minimum": min(currents) if currents else None,
            "maximum": max(currents) if currents else None,
        }

        if len(currents) == self.count:
            status = "passed"
        elif currents:
            status = "partial"
        else:
            status = "failed"

        run_id = str(uuid.uuid4())
        result = {
            "run_id": run_id,
            "ammeter": ammeter_type,
            "status": status,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "measurements_count": self.count,
                "total_duration_seconds": self.duration,
                "sampling_frequency_hz": self.frequency,
            },
            "measurements": measurements,
            "errors": errors,
            "timing_warnings": timing_warnings,
            "statistics": stats,
        }

        path = self.output_dir / f"{ammeter_type}_{run_id}.json"
        with path.open("w", encoding="utf-8") as file:
            json.dump(result, file, indent=2)

        return result

    def load_history(self, ammeter_type: str) -> list:
        """Read previous JSON reports for one ammeter (oldest first)."""
        reports = []
        for path in self.output_dir.glob(f"{ammeter_type}_*.json"):
            with path.open("r", encoding="utf-8") as file:
                reports.append(json.load(file))
        return sorted(reports, key=lambda item: item["started_at"])