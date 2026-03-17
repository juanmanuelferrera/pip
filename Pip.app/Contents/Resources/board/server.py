#!/usr/bin/env python3
"""Board — serves UI, launches apps, tracks usage."""

import http.server
import subprocess
import urllib.parse
import json
import os
import time
import glob
import plistlib

PORT = 9111
BOARD_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_FILE = os.path.join(BOARD_DIR, 'usage.json')
ICONS_DIR = os.path.join(BOARD_DIR, 'icons')

def scan_apps():
    """Scan /Applications for all apps and extract icons."""
    apps = []
    search_paths = ['/Applications', '/System/Applications', '/System/Applications/Utilities']
    seen = set()
    for base in search_paths:
        for app_path in glob.glob(os.path.join(base, '*.app')):
            name = os.path.basename(app_path).replace('.app', '')
            if name in seen or name.startswith('.'):
                continue
            seen.add(name)
            # Extract icon if not exists
            icon_path = os.path.join(ICONS_DIR, f'{name}.png')
            if not os.path.exists(icon_path):
                try:
                    plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
                    if os.path.exists(plist_path):
                        with open(plist_path, 'rb') as f:
                            plist = plistlib.load(f)
                        icon_file = plist.get('CFBundleIconFile', 'AppIcon')
                        if not icon_file.endswith('.icns'):
                            icon_file += '.icns'
                        icns = os.path.join(app_path, 'Contents', 'Resources', icon_file)
                        if os.path.exists(icns):
                            subprocess.run(['sips', '-s', 'format', 'png', '-z', '256', '256',
                                          icns, '--out', icon_path],
                                         capture_output=True, timeout=5)
                except Exception:
                    pass
            if os.path.exists(icon_path):
                apps.append(name)
    return sorted(apps)

# Scan on startup
ALL_APPS = scan_apps()

def load_usage():
    try:
        with open(USAGE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_usage(usage):
    with open(USAGE_FILE, 'w') as f:
        json.dump(usage, f, indent=2)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BOARD_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/board' or self.path == '/':
            self.path = '/index.html'
            return super().do_GET()
        elif self.path == '/strip':
            self.path = '/strip.html'
            return super().do_GET()
        elif self.path.startswith('/launch/'):
            app = urllib.parse.unquote(self.path[8:])
            subprocess.Popen(['open', '-a', app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Track usage
            usage = load_usage()
            if app not in usage:
                usage[app] = {"count": 0, "last": 0}
            usage[app]["count"] += 1
            usage[app]["last"] = time.time()
            save_usage(usage)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "app": app}).encode())
        elif self.path == '/toggle-strip':
            subprocess.Popen(['osascript', '-e',
                'tell application "System Events" to keystroke space using control down'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path == '/hide':
            subprocess.Popen(['osascript', '-e', 'tell application "Arc" to set visible to false'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        elif self.path == '/apps':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(ALL_APPS).encode())
        elif self.path == '/rescan':
            ALL_APPS.clear()
            ALL_APPS.extend(scan_apps())
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "count": len(ALL_APPS)}).encode())
        elif self.path == '/usage':
            usage = load_usage()
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(usage).encode())
        else:
            return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    print(f"Board running on http://localhost:{PORT}")
    server.serve_forever()
