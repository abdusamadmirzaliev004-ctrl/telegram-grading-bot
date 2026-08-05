import subprocess
import time
import re
import os

print("Starting localtunnel...")
process = subprocess.Popen(
    ["cmd.exe", "/c", "npx -y localtunnel --port 8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

url = None
for line in iter(process.stdout.readline, ''):
    print(line, end='')
    match = re.search(r'https://[a-zA-Z0-9-]+\.loca\.lt', line)
    if match:
        url = match.group(0)
        print(f"\nCaptured HTTPS Tunnel URL: {url}")
        break

if url:
    # Update bot.py with the HTTPS URL
    with open("bot.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace http://localhost:8000 with the HTTPS tunnel URL
    new_content = re.sub(r'mini_app_url = ".*?"', f'mini_app_url = "{url}"', content)
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Updated bot.py with new HTTPS Mini App URL.")
