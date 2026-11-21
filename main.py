"""Start the emulators and run a test on each one."""

import socket
import threading
import time

from Ammeters.Circutor_Ammeter import CircutorAmmeter
from Ammeters.Entes_Ammeter import EntesAmmeter
from Ammeters.Greenlee_Ammeter import GreenleeAmmeter
from src.testing.test_framework import AmmeterTestFramework


AMMETERS = {
    "greenlee": GreenleeAmmeter,
    "entes": EntesAmmeter,
    "circutor": CircutorAmmeter,
}


def start_emulators(framework):
    """Run each TCP emulator on its own daemon thread."""
    for name, emulator_class in AMMETERS.items():
        port = int(framework.config["ammeters"][name]["port"])
        emulator = emulator_class(port)
        thread = threading.Thread(target=emulator.start_server, daemon=True)
        thread.start()

        # Wait until the server accepts connections, not a fixed 5-second delay.
        for attempt in range(40):
            try:
                with socket.create_connection(("localhost", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError(f"{name} emulator did not start on port {port}")


def main():
    framework = AmmeterTestFramework()
    start_emulators(framework)
    print("\nStarting measurements...\n")

    for name in AMMETERS:
        report = framework.run_test(name)
        stats = report["statistics"]
        mean_text = f"{stats['mean']:.4f} A" if stats["mean"] is not None else "N/A"
        print(f"{name.upper()}: {report['status']} | "
              f"{len(report['measurements'])}/{framework.count} readings | "
              f"mean: {mean_text}")
        if report["errors"]:
            print(f"  Measurement errors: {report['errors']}")
        if report["timing_warnings"]:
            print(f"  Timing warning: {len(report['timing_warnings'])} sample(s) "
                  "started after the configured duration. "
                  "See the JSON report for details.")

    print("\nFull JSON reports saved in results/")


if __name__ == "__main__":
    main()