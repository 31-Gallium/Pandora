import subprocess
print("Starting Pandora...")
result = subprocess.run(["python", "main.py"], capture_output=True, text=True)
with open("pandora_crash_report.log", "w") as out:
    out.write("RETURN CODE: " + str(result.returncode) + "\n")
    out.write("STDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr)
print("Pandora exited with code", result.returncode)
