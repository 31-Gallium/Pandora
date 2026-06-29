# `run_pandora.py` Summary

## Role in Architecture
A very simple wrapper script to launch the main Pandora application and capture output for crash reporting.

## Key Classes and Functions
- Uses `subprocess.run` to execute `python main.py`.
- Captures standard output and standard error from the execution.
- If the application exits, it writes the exit code, STDOUT, and STDERR to a local file named `pandora_crash_report.log`.

## Dependencies and Interactions
- Relies on the standard `subprocess` module.
- Directly runs `main.py`.
