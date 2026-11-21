# Design choices and bug fixes

The goal was a maintainable framework with minimal dependencies and clear testing behavior.

## What was fixed in the starter project

1. **Incorrect ports:** the starter `main.py` used 5001/5002/5003; the README and emulators' intended setup use **5000/5001/5002**.
2. **Incorrect commands:** the sample calls omitted required suffixes. The commands configured now match each emulator's `get_current_command` property. In particular, CIRCUTOR needs `-current`, which was missing in the general README description.
3. **Missing return value:** the original `client.py` printed the received value instead of returning a float. The client now returns `float` and validates missing/invalid/non-finite values.
4. **Incomplete framework:** `run_test` was only a placeholder and the sample runner called it without a device name. Both are now implemented.
5. **Nonfunctional config:** sampling and device settings were placeholders. They now contain usable values.
6. **Port reuse problem:** `SO_REUSEADDR` was added to the base emulator socket so a test can be restarted immediately after the previous process exits.
7. **Startup race:** the runner checks whether each TCP server is ready instead of sleeping for a hard-coded 5 seconds.

## Simple structure

- The emulators are responsible only for simulating values.
- The common TCP client is responsible only for sending a request and converting the response to a float.
- `AmmeterTestFramework` samples, calculates statistics, and archives reports.
- `main.py` starts servers and prints short summaries.

This avoids unnecessary inheritance, databases, and complex concurrency in the test framework.

## Timing

`time.monotonic()` is used to schedule requests because system clock changes do not affect it. Each request has a 2-second socket timeout. If a request fails, the error is added to the report and the remaining attempts continue (unless the sampling window has expired). Measured sample timestamps and actual runtime may vary slightly because Python and TCP timing is not hard real-time.

## Statistics

The framework uses the standard Python `statistics` module: `mean`, `median`, `stdev`, `min`, and `max`. It reports standard deviation as `null` when fewer than two valid measurements exist. If all requests fail, all statistics are `null`.

## History and archiving

Every run is written to a separate JSON file with a UUID. It can be loaded with `load_history()` and compared via `python -m examples.show_history`. JSON is portable and human-readable; no database is needed for this exercise.

## Testing

The six pytest tests cover:

1. Correct statistical calculations, JSON writing and history loading.
2. Rejection of unknown ammeter types.
3. Rejection of impossible sampling settings.
4. A complete connection failure.
5. A partially successful test run.
6. A real TCP exchange returning a float.

`pytest` is needed only for these tests. The runtime dependency is only PyYAML.

## Intentionally omitted bonuses

Visualization, fault injection inside the emulator, and relative accuracy rankings are optional. They were omitted to keep the mandatory solution understandable. A fair **accuracy** comparison would require all devices to receive the same known reference current; independent random outputs cannot establish which device is more accurate.
