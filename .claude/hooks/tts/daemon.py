#!/usr/bin/env python3
"""
claude-code-tts — TTS daemon
Persistent background process. Keeps model loaded. Serves speech via TCP.

Protocol (JSON lines over localhost — port derived from install dir):
  {"cmd": "speak", "text": "...", "voice": "af_heart", "speed": 1.0, "project": "repo-name"}
  {"cmd": "stop"}
  {"cmd": "ping"}
  {"cmd": "quit"}

Queue behavior: at most one pending item per project key.
New message from same project replaces its queued slot; different projects line up.

Engines:
  Primary:  edge-tts  (free, cloud, Microsoft neural voices, ~0 RAM)
  Fallback: kokoro-onnx (local, offline — optional, activates if edge-tts fails)
"""

import json
import os
import socket
import sys
import threading
import time

# Limit ONNX inference threads — prevents all-core spike on synthesis.
# Must be set before kokoro_onnx / onnxruntime is imported.
os.environ.setdefault('OMP_NUM_THREADS', '6')
os.environ.setdefault('ONNXRUNTIME_NUM_THREADS', '6')

HOST = '127.0.0.1'
DAEMON_DIR = os.path.dirname(os.path.abspath(__file__))

# Port is derived from install location — each install gets its own daemon port,
# so multiple projects with local installs don't collide.
import hashlib as _hashlib
PORT = 49152 + (int(_hashlib.md5(DAEMON_DIR.encode()).hexdigest(), 16) % 16384)
PID_FILE = os.path.join(DAEMON_DIR, 'daemon.pid')
# Model search: project-local first, then global ~/.claude/hooks/tts/models/
_GLOBAL_MODELS = os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'tts', 'models')
_LOCAL_MODELS = os.path.join(DAEMON_DIR, 'models')

def _find_model(filename):
    for d in (_LOCAL_MODELS, _GLOBAL_MODELS):
        p = os.path.join(d, filename)
        if os.path.exists(p):
            return p
    return os.path.join(_LOCAL_MODELS, filename)  # fallback path (will fail gracefully)

MODEL_PATH = _find_model('kokoro-v1.0.onnx')
VOICES_PATH = _find_model('voices-v1.0.bin')

# Maps kokoro voice names → closest Edge TTS neural voice (gender/personality match)
EDGE_VOICE_MAP = {
    'af_heart':   'en-US-AriaNeural',        # warm, natural female
    'af_bella':   'en-US-MichelleNeural',    # polished female
    'af_sarah':   'en-US-SaraNeural',        # professional female
    'af_sky':     'en-US-JennyNeural',       # friendly, conversational
    'af_nova':    'en-US-MonicaNeural',      # energetic female
    'am_michael': 'en-US-GuyNeural',         # natural, authoritative male
    'am_adam':    'en-US-DavisNeural',       # deep male
    'am_echo':    'en-US-TonyNeural',        # casual male
    'am_eric':    'en-US-EricNeural',        # confident male
    'am_liam':    'en-US-RyanNeural',        # young, energetic male
    'am_onyx':    'en-US-ChristopherNeural', # deep, authoritative male
}

# Speech state
_kokoro = None  # None if not installed or failed to load

# Queue: list of {'project': str|None, 'text': str, 'voice': str, 'speed': float}
# Invariant: at most one entry per project key.
_queue_lock = threading.Lock()
_play_queue = []
_play_event = threading.Event()   # signals player loop that queue has items
_current_stop = threading.Event() # signals player to abort current synthesis/playback


def _log(msg, path='debug.log'):
    log_path = os.path.join(DAEMON_DIR, path)
    ts = time.strftime('%H:%M:%S') + f'.{int(time.time()*1000)%1000:03d}'
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f'[{ts}] {msg}\n')
    except Exception:
        pass

def _log_error(msg):
    _log(msg, path='daemon.log')


def _play_blocking(samples, sr):
    """Play audio using a dedicated OutputStream — no global sounddevice state.
    Checks _current_stop every ~40ms. Returns True if fully played."""
    import sounddevice as sd
    import traceback
    if samples is None or _current_stop.is_set():
        _log(f'_play_blocking: skipped (stop={_current_stop.is_set()} samples_none={samples is None})')
        return False

    channels = 1 if samples.ndim == 1 else samples.shape[1]
    total_frames = len(samples)
    duration_s = total_frames / sr
    _log(f'_play_blocking: START sr={sr} frames={total_frames} dur={duration_s:.2f}s channels={channels} dtype={samples.dtype}')

    chunk_frames = 1024  # ~40ms at 24kHz — responsive stop without audible gaps
    stream = sd.OutputStream(samplerate=sr, channels=channels, dtype=samples.dtype)
    stream.start()
    try:
        for i in range(0, total_frames, chunk_frames):
            if _current_stop.is_set():
                _log(f'_play_blocking: ABORTED at frame {i}/{total_frames}')
                stream.abort()
                return False
            stream.write(samples[i:i + chunk_frames])
        _log(f'_play_blocking: all chunks written, calling stream.stop()')
        stream.stop()   # drain hardware buffer cleanly before returning
        _log(f'_play_blocking: COMPLETE')
        return True
    except Exception:
        _log(f'_play_blocking: EXCEPTION\n{traceback.format_exc()}')
        try:
            stream.abort()
        except Exception:
            pass
        raise
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _chunk_text(text, max_chars=1500):
    """Split text into sentence-boundary chunks, each under max_chars.
    Kokoro-onnx has a 510-token (~2000 char) hard limit — chunking prevents
    IndexError that silently kills synthesis and causes apparent interruptions."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = ''
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            sentence = sentence[:max_chars]
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = (current + ' ' + sentence).strip() if current else sentence
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def _speed_to_rate(speed):
    """Convert kokoro speed (1.0 = normal) to edge-tts rate string (e.g. '+10%')."""
    pct = int((speed - 1.0) * 100)
    return f'{pct:+d}%'


async def _edge_async(text, edge_voice, rate):
    import edge_tts
    communicate = edge_tts.Communicate(text, edge_voice, rate=rate)
    audio_bytes = b''
    async for chunk in communicate.stream():
        if chunk['type'] == 'audio':
            audio_bytes += chunk['data']
    return audio_bytes


def _synthesize_edge(text, voice, speed):
    """Synthesize via Edge TTS. Returns (samples_float32, sample_rate) or raises."""
    import asyncio
    import miniaudio
    import numpy as np
    edge_voice = EDGE_VOICE_MAP.get(voice, 'en-US-AriaNeural')
    rate = _speed_to_rate(speed)
    audio_bytes = asyncio.run(_edge_async(text, edge_voice, rate))
    if not audio_bytes:
        raise RuntimeError('edge-tts returned empty audio')
    decoded = miniaudio.decode(audio_bytes, output_format=miniaudio.SampleFormat.FLOAT32, nchannels=1)
    samples = np.frombuffer(decoded.samples, dtype=np.float32).copy()
    return samples, decoded.sample_rate


def _player_loop():
    """Persistent player thread: drains _play_queue one item at a time.
    Never interrupted by do_speak() — only do_stop() can cut off playback."""
    import traceback

    while True:
        _play_event.wait()

        while True:
            with _queue_lock:
                if not _play_queue:
                    _play_event.clear()
                    _current_stop.clear()  # ready for next message after stop
                    _log(f'player: queue empty, waiting')
                    break
                item = _play_queue.pop(0)
                _log(f'player: popped project={item["project"]!r} queue_remaining={len(_play_queue)}')

            if _current_stop.is_set():
                _log(f'player: stop set at item start, breaking')
                break
            _current_stop.clear()

            # --- Edge TTS (primary): full text, no chunking needed ---
            edge_ok = False
            if not _current_stop.is_set():
                try:
                    _log(f'player: edge-tts project={item["project"]!r} text_len={len(item["text"])}')
                    samples, sr = _synthesize_edge(item['text'], item['voice'], item['speed'])
                    _log(f'player: edge-tts done stop={_current_stop.is_set()}')
                    if not _current_stop.is_set():
                        _play_blocking(samples, sr)
                    edge_ok = True
                except Exception:
                    _log('player: edge-tts failed, falling back to kokoro')
                    _log_error(traceback.format_exc())

            # --- Kokoro fallback: chunked to stay under 510-token limit ---
            if not edge_ok and not _current_stop.is_set():
                if _kokoro is None:
                    _log('player: edge-tts failed and kokoro not available — skipping item')
                else:
                    chunks = _chunk_text(item['text'])
                    _log(f'player: kokoro fallback chunks={len(chunks)}')
                    for chunk_idx, chunk in enumerate(chunks):
                        if _current_stop.is_set():
                            _log(f'player: stop set before kokoro chunk {chunk_idx}')
                            break
                        try:
                            _log(f'player: kokoro chunk {chunk_idx+1}/{len(chunks)} len={len(chunk)}')
                            samples, sr = _kokoro.create(
                                chunk, voice=item['voice'],
                                speed=item['speed'], lang='en-us'
                            )
                            _log(f'player: kokoro done chunk={chunk_idx+1}')
                            if not _current_stop.is_set() and samples is not None:
                                _play_blocking(samples, sr)
                        except Exception:
                            _log_error(traceback.format_exc())


def do_speak(text, voice='af_heart', speed=1.0, project=None):
    """Queue speech. Replaces any existing queued item for the same project key."""
    with _queue_lock:
        _play_queue[:] = [i for i in _play_queue if i['project'] != project]
        _play_queue.append({'project': project, 'text': text, 'voice': voice, 'speed': speed})
        qsize = len(_play_queue)
    _log(f'do_speak: project={project!r} text_len={len(text)} queue_size={qsize}')
    _play_event.set()


def do_stop():
    """Stop all speech and clear the queue.
    _play_blocking() checks _current_stop between 40ms chunks — stops within ~40ms."""
    with _queue_lock:
        _play_queue.clear()
    _log(f'do_stop: CALLED — clearing queue and setting stop event')
    _current_stop.set()


def handle_client(conn):
    try:
        data = b''
        conn.settimeout(5.0)
        while b'\n' not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        msg = json.loads(data.decode('utf-8').strip())
        cmd = msg.get('cmd', '')

        if cmd == 'speak':
            text = msg.get('text', '').strip()
            voice = msg.get('voice', 'af_heart')
            speed = float(msg.get('speed', 1.0))
            project = msg.get('project', None)
            conn.send(json.dumps({'ok': True}).encode() + b'\n')
            conn.close()
            if text:
                do_speak(text, voice, speed, project)
            return

        elif cmd == 'stop':
            do_stop()
            conn.send(json.dumps({'ok': True}).encode() + b'\n')

        elif cmd == 'ping':
            conn.send(json.dumps({'ok': True, 'pid': os.getpid()}).encode() + b'\n')

        elif cmd == 'quit':
            conn.send(json.dumps({'ok': True}).encode() + b'\n')
            conn.close()
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
            os._exit(0)

        else:
            conn.send(json.dumps({'ok': False, 'error': f'unknown cmd: {cmd}'}).encode() + b'\n')

    except Exception as e:
        try:
            conn.send(json.dumps({'ok': False, 'error': str(e)}).encode() + b'\n')
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    global _kokoro

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Set process to below-normal priority so synthesis yields to foreground work.
    if sys.platform == 'win32':
        import ctypes
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        ctypes.windll.kernel32.SetPriorityClass(-1, BELOW_NORMAL_PRIORITY_CLASS)
    else:
        try:
            os.nice(10)
        except Exception:
            pass

    # Load kokoro-onnx if available (optional offline fallback).
    # Daemon starts even if kokoro is not installed — edge-tts handles primary speech.
    try:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
        sys.stderr.write('kokoro-onnx loaded (offline fallback active)\n')
    except ImportError:
        sys.stderr.write('kokoro-onnx not installed — edge-tts only (no offline fallback)\n')
    except Exception as e:
        sys.stderr.write(f'WARNING: kokoro-onnx failed to load: {e} — edge-tts only\n')

    threading.Thread(target=_player_loop, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except OSError as e:
        sys.stderr.write(f'ERROR: Cannot bind {HOST}:{PORT}: {e}\n')
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        sys.exit(1)

    server.listen(10)

    try:
        while True:
            conn, _ = server.accept()
            t = threading.Thread(target=handle_client, args=(conn,), daemon=True)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        server.close()


if __name__ == '__main__':
    main()
