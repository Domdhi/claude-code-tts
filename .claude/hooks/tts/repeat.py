#!/usr/bin/env python3
"""
claude-code-tts — UserPromptSubmit hook
Intercepts /repeat and /voice:stop commands.
  /repeat       → replays the last spoken response
  /voice:stop   → stops speech immediately
"""

import json
import sys
import os
import socket
import subprocess
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
ON_FILE = os.path.join(HOOK_DIR, 'on')
LAST_FILE = os.path.join(HOOK_DIR, 'last.txt')
VOICES_FILE = os.path.join(HOOK_DIR, 'voices.json')
DAEMON_SCRIPT = os.path.join(HOOK_DIR, 'daemon.py')

DAEMON_HOST = '127.0.0.1'
import hashlib as _hashlib
DAEMON_PORT = 49152 + (int(_hashlib.md5(HOOK_DIR.encode()).hexdigest(), 16) % 16384)


def _start_daemon():
    kwargs = {
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
    }
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, DAEMON_SCRIPT], **kwargs)
    for _ in range(40):
        time.sleep(0.2)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((DAEMON_HOST, DAEMON_PORT))
            s.close()
            return True
        except Exception:
            pass
    return False


def send_to_daemon(cmd_dict):
    for attempt in range(2):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect((DAEMON_HOST, DAEMON_PORT))
            s.send(json.dumps(cmd_dict).encode() + b'\n')
            resp = s.recv(1024)
            s.close()
            return json.loads(resp.decode().strip()).get('ok', False)
        except ConnectionRefusedError:
            if attempt == 0:
                _start_daemon()
        except Exception:
            return False
    return False


def load_default_voice():
    if os.path.exists(VOICES_FILE):
        try:
            with open(VOICES_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f).get('default', {})
                return cfg.get('voice', 'af_heart'), float(cfg.get('speed', 1.0))
        except Exception:
            pass
    return 'af_heart', 1.0


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    prompt = data.get('prompt', '').strip()

    if prompt in ('/voice stop', '/voice:stop', '/stop'):
        send_to_daemon({'cmd': 'stop'})
        print(json.dumps({'decision': 'block', 'reason': ''}))
        sys.exit(0)

    if prompt not in ('/repeat', '/voice repeat', '/voice:repeat'):
        sys.exit(0)

    # Replay last spoken text
    if os.path.exists(LAST_FILE):
        try:
            with open(LAST_FILE, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            if text:
                voice, speed = load_default_voice()
                send_to_daemon({'cmd': 'speak', 'text': text, 'voice': voice, 'speed': speed})
        except Exception:
            pass

    print(json.dumps({'decision': 'block', 'reason': ''}))
    sys.exit(0)


if __name__ == '__main__':
    main()
