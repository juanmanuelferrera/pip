#!/usr/bin/env python3
"""Pip monitor — tracks which app is in the foreground every 5 seconds."""

import subprocess
import json
import os
import time

BOARD_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(BOARD_DIR, 'usage.json')

def load_usage():
    try:
        with open(USAGE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_usage(usage):
    with open(USAGE_FILE, 'w') as f:
        json.dump(usage, f, indent=2)

def get_frontmost_app():
    """Get the name of the frontmost app."""
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3
        )
        name = result.stdout.strip()
        # Skip system processes and Pip itself
        skip = {'Finder', 'loginwindow', 'Dock', 'SystemUIServer', 'ControlCenter',
                'Spotlight', 'Board', 'Pip', 'BoardStrip', 'WindowManager',
                'NotificationCenter', 'SecurityAgent'}
        if name and name not in skip:
            return name
    except:
        pass
    return None

def main():
    last_app = None
    last_time = time.time()

    while True:
        time.sleep(5)
        app = get_frontmost_app()
        if not app:
            continue

        now = time.time()

        if app != last_app:
            # App switched — record usage for previous app
            if last_app:
                usage = load_usage()
                if last_app not in usage:
                    usage[last_app] = {"count": 0, "last": 0, "seconds": 0}
                if "seconds" not in usage[last_app]:
                    usage[last_app]["seconds"] = 0
                usage[last_app]["seconds"] += int(now - last_time)
                usage[last_app]["last"] = now
                save_usage(usage)

            last_app = app
            last_time = now
        else:
            # Same app still in foreground — update every 30 seconds
            if now - last_time >= 30:
                usage = load_usage()
                if app not in usage:
                    usage[app] = {"count": 0, "last": 0, "seconds": 0}
                if "seconds" not in usage[app]:
                    usage[app]["seconds"] = 0
                usage[app]["seconds"] += int(now - last_time)
                usage[app]["last"] = now
                save_usage(usage)
                last_time = now

if __name__ == '__main__':
    main()
