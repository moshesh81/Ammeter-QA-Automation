# Ammeter QA Test Framework

A simple Python framework that tests three existing TCP ammeter emulators: **Greenlee**, **ENTES**, and **CIRCUTOR**.

The original exercise specification is in `Exam/ammeter-test-specification.md`.

## Requirements

- Python 3.10 or newer
- PyYAML (reads `config/config.yaml`)
- pytest (used only to run automated tests)

No database, web framework, or numerical/plotting libraries are required.

## Run it

From the project folder:

```bash
python -m pip install -r requirements.txt
python main.py
```

`main.py` starts the three TCP emulators, takes seven measurements from each at 2 Hz, prints a summary, and saves detailed JSON reports in `results/`.

Example summary (random values change on every run):

```text
GREENLEE: passed | 6/6 readings | mean: 0.1018 A
ENTES: passed | 6/6 readings | mean: 91.4539 A
CIRCUTOR: passed | 6/6 readings | mean: 0.0407 A
```

To display and compare the means from previous runs:

```bash
python -m examples.show_history
```

To run automated checks:

```bash
python -m pytest -q
```

## Configuration

Edit `config/config.yaml` to change the ammeter ports/commands and sampling parameters.

```yaml
testing:
  sampling:
    measurements_count: 6
    total_duration_seconds: 3
    sampling_frequency_hz: 2
```

- **Count**: the number of measurement attempts per ammeter.
- **Frequency**: when to start each attempt. At 2 Hz, targets are 0, 0.5, 1, 1.5, 2, and 2.5 seconds.
- **Duration**: the maximum sampling window. A measurement may take additional time to return, so this is a limit for starting a request, not a hard runtime deadline.

The framework raises a configuration error if the count cannot fit inside the sampling window at the requested frequency. Tests run sequentially for the three devices.

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Starts the emulators and runs all tests |
| `Ammeters/` | Existing device emulators; the common client was fixed |
| `config/config.yaml` | Ports, commands, and sampling settings |
| `src/testing/test_framework.py` | Sampling, statistics, error handling, and JSON saving/loading |
| `examples/show_history.py` | Displays previous results for comparison |
| `tests/test_framework.py` | seven automated tests |
| `sample_results/` | Real example JSON reports from a completed run |
| `DESIGN.md` | Design decisions, fixes, and limitations |

## What the report contains

Every run has a unique `run_id`, timestamps, settings, measurements, errors, and statistics (mean, median, sample standard deviation, minimum, maximum). Status means:

- `passed`: all measurement requests returned valid numbers.
- `partial`: some requests succeeded and some failed.
- `failed`: no valid measurements returned.

**Important:** `passed` means successful collection, **not validated physical accuracy**.

Actual device values are intentionally random, and each emulator simulates a different measurement principle. Accuracy cannot be established without a known reference current applied consistently to all devices.

## Notes

The emulators require localhost ports 5000, 5001 and 5002. If another application is using one of these ports, change the port in `config/config.yaml`.

If testing on Windows, run the commands in PowerShell or Command Prompt. No special shell features are required.
