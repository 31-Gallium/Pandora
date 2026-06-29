import sys
import traceback
sys.stderr = open('crash_wrapper_stderr.log', 'w')
sys.stdout = open('crash_wrapper_stdout.log', 'w')
try:
    import main
except Exception as e:
    traceback.print_exc()
