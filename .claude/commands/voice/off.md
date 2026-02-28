Disable TTS voice output. Run the following Python command using the Bash tool (it stops any playing audio and removes the enable file), then respond with only: "TTS disabled."

```bash
python -c "
import socket, json, hashlib, os

for hook_dir in [
    os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'tts'),
    os.path.join(os.getcwd(), '.claude', 'hooks', 'tts'),
]:
    if not os.path.isdir(hook_dir):
        continue
    port = 49152 + (int(hashlib.md5(hook_dir.encode()).hexdigest(), 16) % 16384)
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(('127.0.0.1', port))
        s.sendall(json.dumps({'cmd': 'stop'}).encode() + b'\n')
        s.close()
    except Exception:
        pass
    on_file = os.path.join(hook_dir, 'on')
    try:
        os.remove(on_file)
    except Exception:
        pass
" 2>/dev/null || true
```
