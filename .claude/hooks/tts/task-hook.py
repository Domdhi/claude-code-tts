#!/usr/bin/env python3
"""
claude-code-tts — PostToolUse:Task hook
Fires after a Task tool call completes. Reads subagent_type from tool_input
to look up the agent's voice — no [agent-name]: prefix required.
"""

import json
import sys
import re
import os
import socket
import subprocess
import time

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
ON_FILE = os.path.join(HOOK_DIR, 'on')
VOICES_FILE = os.path.join(HOOK_DIR, 'voices.json')
SESSIONS_FILE = os.path.join(HOOK_DIR, 'sessions.json')
DAEMON_SCRIPT = os.path.join(HOOK_DIR, 'daemon.py')

DAEMON_HOST = '127.0.0.1'
import hashlib as _hashlib
DAEMON_PORT = 49152 + (int(_hashlib.md5(HOOK_DIR.encode()).hexdigest(), 16) % 16384)


def strip_markdown(text):
    text = re.sub(r'```[\w]*\n.*?```', '[code block]', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', lambda m: m.group(0)[1:-1], text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = _sanitize_unicode(text)
    return text.strip()


def _sanitize_unicode(text):
    replacements = {
        '→': ', ', '←': ', ', '↑': ', ', '↓': ', ',
        '⇒': ', ', '⇐': ', ', '⇔': ', ',
        '—': ', ', '–': ', ', '…': '...',
        '\u2019': "'", '\u2018': "'",
        '\u201c': '"', '\u201d': '"',
        '•': '', '·': '',
        '✓': 'yes', '✗': 'no', '✅': 'yes', '❌': 'no',
        '🔴': '', '🟡': '', '🟢': '', '⭐': '',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text


def extract_text_from_response(tool_response):
    """Pull plain text out of whatever shape the tool_response takes."""
    if isinstance(tool_response, str):
        return tool_response.strip()

    if isinstance(tool_response, dict):
        content = tool_response.get('content', tool_response.get('output', ''))
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get('text', ''))
                elif isinstance(block, str):
                    parts.append(block)
            return '\n'.join(p for p in parts if p).strip()

    return ''


def load_voices():
    if os.path.exists(VOICES_FILE):
        try:
            with open(VOICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'default': {'voice': 'af_heart', 'speed': 1.0}}


_SESSION_TTL = 7200


def _get_session_id(data):
    sid = data.get('session_id', '')
    if sid:
        return sid
    tp = data.get('transcript_path', '')
    if tp:
        return os.path.splitext(os.path.basename(tp))[0]
    return ''


def _get_session_voice(session_id, voices):
    """Assign a voice from session_pool if configured. Returns voice key or None."""
    pool = voices.get('session_pool')
    if not pool or not session_id:
        return None

    sessions = {}
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
        except Exception:
            sessions = {}

    now = time.time()
    sessions = {k: v for k, v in sessions.items()
                if now - v.get('last_seen', 0) < _SESSION_TTL}

    if session_id in sessions:
        sessions[session_id]['last_seen'] = now
        try:
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f)
        except Exception:
            pass
        return sessions[session_id].get('voice')

    used = {v.get('voice') for v in sessions.values()}
    voice = None
    for v in pool:
        if v not in used:
            voice = v
            break

    if voice is None:
        pool_sessions = {k: v for k, v in sessions.items() if v.get('voice') in pool}
        if pool_sessions:
            oldest = min(pool_sessions, key=lambda k: pool_sessions[k].get('last_seen', 0))
            voice = pool_sessions[oldest]['voice']
        else:
            voice = pool[0]

    sessions[session_id] = {'voice': voice, 'last_seen': now}
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f)
    except Exception:
        pass
    return voice


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
            s.sendall(json.dumps(cmd_dict).encode() + b'\n')
            resp = s.recv(1024)
            s.close()
            return json.loads(resp.decode().strip()).get('ok', False)
        except ConnectionRefusedError:
            if attempt == 0:
                _start_daemon()
        except Exception:
            return False
    return False


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    if not os.path.exists(ON_FILE):
        sys.exit(0)

    if data.get('tool_name') != 'Task':
        sys.exit(0)

    # Determine agent from tool_input.subagent_type — no prefix required
    tool_input = data.get('tool_input', {})
    agent_name = tool_input.get('subagent_type', '')

    tool_response = data.get('tool_response', '')
    raw_text = extract_text_from_response(tool_response)

    if not raw_text:
        sys.exit(0)

    # Strip [agent-name]: prefix if the agent included it anyway
    raw_text = re.sub(r'^\[[^\]]+\]:\s*', '', raw_text)

    cleaned = strip_markdown(raw_text)
    if not cleaned:
        sys.exit(0)

    voices = load_voices()
    cfg = voices.get(agent_name)
    if not cfg:
        # No agent-specific voice — try session pool, then default
        session_id = _get_session_id(data)
        pool_voice = _get_session_voice(session_id, voices)
        if pool_voice:
            default_speed = float(voices.get('default', {}).get('speed', 1.0))
            cfg = {'voice': pool_voice, 'speed': default_speed}
        else:
            cfg = voices.get('default') or {}
    voice = cfg.get('voice', 'af_heart')
    speed = float(cfg.get('speed', 1.0))

    # Use tool_use_id as a stable per-task identity so rapid task completions
    # replace each other in the queue rather than stacking.
    task_id = data.get('tool_use_id') or data.get('session_id') or 'task'
    send_to_daemon({'cmd': 'speak', 'text': cleaned, 'voice': voice, 'speed': speed, 'project': task_id})
    sys.exit(0)


if __name__ == '__main__':
    main()
