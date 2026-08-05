import subprocess
import re
import time

print("Starting SSH localhost.run tunnel...")
proc = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:localhost:8000", "nokey@localhost.run"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

url = None
while True:
    line = proc.stdout.readline()
    if not line:
        break
    line_str = line.strip()
    print(line_str)
    # Match domain like https://adf25cafa1a58e.lhr.life or https://xxxx.lhrtunnel.link
    match = re.search(r'https://[a-zA-Z0-9]{8,}\.lhr\.life', line_str) or re.search(r'https://[a-zA-Z0-9]{8,}\.lhrtunnel\.link', line_str)
    if match:
        url = match.group(0)
        print(f"\nSUCCESS! Captured HTTPS Tunnel URL: {url}")
        break

if url:
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r'mini_app_url = ".*?"', f'mini_app_url = "{url}"', content)
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Updated bot.py with active HTTPS URL.")
    # Keep process running in background
    proc.wait()
