#!/usr/bin/env python3
"""
claude-code-tts — Stop hook
Fires when Claude finishes a response. Reads the last assistant message from
the transcript and sends it to the TTS daemon for playback.
Starts the daemon automatically if it's not running.
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
LAST_FILE = os.path.join(HOOK_DIR, 'last.txt')
VOICES_FILE = os.path.join(HOOK_DIR, 'voices.json')
SESSIONS_FILE = os.path.join(HOOK_DIR, 'sessions.json')
DAEMON_SCRIPT = os.path.join(HOOK_DIR, 'daemon.py')

DAEMON_HOST = '127.0.0.1'
import hashlib as _hashlib
DAEMON_PORT = 49152 + (int(_hashlib.md5(HOOK_DIR.encode()).hexdigest(), 16) % 16384)

READ_ALL_CHAIN = False  # True = speak all assistant messages in chain, False = last only


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
    """Replace unicode symbols that TTS engines can't phonemize with ASCII equivalents."""
    replacements = {
        '→': ', ', '←': ', ', '↑': ', ', '↓': ', ',
        '⇒': ', ', '⇐': ', ', '⇔': ', ',
        '—': ', ', '–': ', ', '…': '...',
        '\u2019': "'", '\u2018': "'",  # smart quotes
        '\u201c': '"', '\u201d': '"',
        '•': '', '·': '',
        '✓': 'yes', '✗': 'no', '✅': 'yes', '❌': 'no',
        '🔴': '', '🟡': '', '🟢': '', '⭐': '',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Strip remaining non-ASCII
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text


def extract_last_assistant_message(transcript_path):
    if not os.path.exists(transcript_path):
        return None
    entries = []
    with open(transcript_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Find index of last real user message (skip tool result entries)
    last_user_idx = -1
    for i, obj in enumerate(entries):
        if obj.get('type') == 'user':
            content = obj.get('message', {}).get('content', [])
            if isinstance(content, list) and content and all(
                isinstance(b, dict) and b.get('type') == 'tool_result'
                for b in content
            ):
                continue
            last_user_idx = i

    texts = []
    for obj in entries[last_user_idx + 1:]:
        if obj.get('type') != 'assistant':
            continue
        content = obj.get('message', {}).get('content', '')
        if isinstance(content, str) and content.strip():
            texts.append(content.strip())
        elif isinstance(content, list):
            parts = [b.get('text', '') for b in content
                     if isinstance(b, dict) and b.get('type') == 'text']
            combined = '\n'.join(parts).strip()
            if combined:
                texts.append(combined)

    if not texts:
        return None
    return '\n\n'.join(texts) if READ_ALL_CHAIN else texts[-1]


def load_voices():
    if os.path.exists(VOICES_FILE):
        try:
            with open(VOICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'default': {'voice': 'af_heart', 'speed': 1.0}}


def get_project_voice(transcript_path, voices):
    """Look up voice by project dir encoded in transcript path.
    Transcript paths look like: .../.claude/projects/c--Users-...-ProjectName/...
    voices.json 'projects' keys are matched as substrings of that encoded segment."""
    projects = voices.get('projects', {})
    if not projects or not transcript_path:
        return None
    norm = transcript_path.replace('\\', '/').lower()
    for key, cfg in projects.items():
        if key.lower() in norm:
            return cfg
    return None


def parse_agent_voice(text, voices, fallback_cfg=None):
    """Parse [AgentName]: prefix. Returns (stripped_text, voice, speed).
    Priority: agent prefix → fallback_cfg (project) → default."""
    match = re.match(r'^\[([^\]]+)\]:\s*', text)
    if match:
        agent = match.group(1)
        text = text[match.end():]
        cfg = voices.get(agent) or fallback_cfg or voices.get('default') or {}
    else:
        cfg = fallback_cfg or voices.get('default') or {}
    voice = cfg.get('voice', 'af_heart')
    speed = float(cfg.get('speed', 1.0))
    return text, voice, speed


_SESSION_TTL = 7200  # prune sessions not seen in 2 hours


def _get_session_id(data):
    """Extract a stable session ID from hook data."""
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
    # Prune stale entries
    sessions = {k: v for k, v in sessions.items()
                if now - v.get('last_seen', 0) < _SESSION_TTL}

    # Already assigned — refresh timestamp and return
    if session_id in sessions:
        sessions[session_id]['last_seen'] = now
        try:
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f)
        except Exception:
            pass
        return sessions[session_id].get('voice')

    # Find voices currently claimed by active sessions
    used = {v.get('voice') for v in sessions.values()}

    # Pick first unused from pool
    voice = None
    for v in pool:
        if v not in used:
            voice = v
            break

    # All claimed — reuse the least recently seen
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
    """Start the TTS daemon as a detached background process."""
    kwargs = {
        'stdout': subprocess.DEVNULL,
        'stderr': subprocess.DEVNULL,
    }
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, DAEMON_SCRIPT], **kwargs)
    # Poll until daemon is ready (up to 8s for model load on first run)
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


PID_FILE = os.path.join(HOOK_DIR, 'daemon.pid')


def _daemon_is_stale():
    """True if daemon.py has been modified since the running daemon started."""
    if not os.path.exists(PID_FILE):
        return False
    try:
        script_mtime = os.path.getmtime(DAEMON_SCRIPT)
        pid_mtime = os.path.getmtime(PID_FILE)
        return script_mtime > pid_mtime
    except Exception:
        return False


def _restart_daemon():
    """Send quit to the old daemon and start a fresh one."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((DAEMON_HOST, DAEMON_PORT))
        s.sendall(json.dumps({'cmd': 'quit'}).encode() + b'\n')
        s.recv(1024)
        s.close()
    except Exception:
        pass
    time.sleep(0.5)
    return _start_daemon()


def send_to_daemon(cmd_dict):
    """Send a command to the daemon. Starts daemon if not running, restarts if stale."""
    if _daemon_is_stale():
        _restart_daemon()

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


def get_project_key(transcript_path):
    """Extract encoded project dir from transcript path.
    e.g. .../.claude/projects/c--Users-dbaca-Repos-MyProject/... → 'c--Users-dbaca-Repos-MyProject'"""
    if not transcript_path:
        return None
    parts = transcript_path.replace('\\', '/').split('/')
    try:
        idx = parts.index('projects')
        return parts[idx + 1]
    except (ValueError, IndexError):
        return None


def speak(text, voice='af_heart', speed=1.0, project=None):
    send_to_daemon({'cmd': 'speak', 'text': text, 'voice': voice, 'speed': speed, 'project': project})


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    if not os.path.exists(ON_FILE):
        sys.exit(0)

    transcript_path = data.get('transcript_path', '')
    if not transcript_path:
        sys.exit(0)

    time.sleep(0.5)
    text = extract_last_assistant_message(transcript_path)
    if not text:
        sys.exit(0)

    cleaned = strip_markdown(text)
    if not cleaned:
        sys.exit(0)

    try:
        with open(LAST_FILE, 'w', encoding='utf-8') as f:
            f.write(cleaned)
    except Exception:
        pass

    voices = load_voices()
    proj_cfg = get_project_voice(transcript_path, voices)

    # Session pool: assign a unique voice per CC instance
    session_id = _get_session_id(data)
    pool_voice = _get_session_voice(session_id, voices)
    default_speed = float(voices.get('default', {}).get('speed', 1.0))
    pool_cfg = {'voice': pool_voice, 'speed': default_speed} if pool_voice else None

    # Priority: agent prefix → project → session pool → default
    fallback = proj_cfg or pool_cfg
    cleaned, voice, speed = parse_agent_voice(cleaned, voices, fallback_cfg=fallback)
    speak(cleaned, voice, speed, project=get_project_key(transcript_path))
    sys.exit(0)


if __name__ == '__main__':
    main()
