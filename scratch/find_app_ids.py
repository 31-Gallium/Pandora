import subprocess
try:
    # List all apps in AppsFolder and their names
    cmd = 'powershell "Get-StartApps | Where-Object { $_.Name -like \'*Sticky*\' -or $_.Name -like \'*Notepad*\' } | Select-Object Name, AppID | ConvertTo-Json"'
    result = subprocess.check_output(cmd, shell=True).decode()
    print(result)
except Exception as e:
    print(f"Error: {e}")
