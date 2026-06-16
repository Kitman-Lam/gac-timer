import sys
import os

# 模拟打包环境的sys.frozen
class FakeFrozen:
    pass

# 模拟PyInstaller的frozen路径
import subprocess
result = subprocess.run(
    ["C:\\Users\\GAC-JD\\Documents\\Timer\\dist\\MeetTimer\\MeetTimer.exe", "--db-path"],
    capture_output=True, text=True, timeout=5
)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
