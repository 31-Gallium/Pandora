import sys
import os
sys.path.append(os.getcwd())
from utils import get_system_mute
print(f"Current mute state: {get_system_mute()}")
