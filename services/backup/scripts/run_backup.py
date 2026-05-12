"""Runs backup.sh once a day at 02:00 local time."""
import subprocess, time, os, datetime, zoneinfo

TZ = os.environ.get("TZ", "Asia/Tehran")

def run():
    subprocess.run(["/usr/local/bin/backup.sh"], check=False)

def seconds_until_next_2am():
    tz = zoneinfo.ZoneInfo(TZ)
    now = datetime.datetime.now(tz)
    target = now.replace(hour=2, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()

print("Backup scheduler started.", flush=True)
run()  # run once on startup so first backup is immediate
while True:
    secs = seconds_until_next_2am()
    print(f"Next backup in {secs/3600:.1f}h", flush=True)
    time.sleep(secs)
    run()
