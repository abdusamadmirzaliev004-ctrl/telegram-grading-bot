import subprocess
import re
import time
import sys

print("Launching Cloudflare Tunnel...")
cmd = ["cloudflared.exe", "tunnel", "--url", "http://localhost:8000"]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

cf_url = None
while True:
    line = proc.stdout.readline()
    if not line:
        break
    line_str = line.strip()
    print(line_str)
    match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line_str)
    if match:
        cf_url = match.group(0)
        print(f"\n==========================================")
        print(f"SUCCESS! CLOUDFLARE HTTPS TUNNEL LIVE: {cf_url}")
        print(f"==========================================\n")
        break

if cf_url:
    # Update bot.py with the Cloudflare URL
    with open("bot.py", "r", encoding="utf-8") as f:
        bot_code = f.read()
    new_bot_code = re.sub(r'mini_app_url = ".*?"', f'mini_app_url = "{cf_url}"', bot_code)
    with open("bot.py", "w", encoding="utf-8") as f:
        f.write(new_bot_code)
    print("Updated bot.py with live Cloudflare HTTPS URL.")

proc.wait()
