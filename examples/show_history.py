"""Compare the mean measurement in previous runs: python -m examples.show_history"""

from src.testing.test_framework import AmmeterTestFramework


def main():
    framework = AmmeterTestFramework()
    for name in framework.config["ammeters"]:
        print(f"\n{name.upper()} (older runs first)")
        for report in framework.load_history(name):
            mean = report["statistics"]["mean"]
            mean_text = f"{mean:.4f} A" if mean is not None else "N/A"
            print(f"  {report['started_at']} | {report['status']} | mean {mean_text}")


if __name__ == "__main__":
    main()
