# claude-code-tts — Installation Reference

Full reference for install options, voice configuration, hooks wiring, and troubleshooting.

---

## Stack

| Package | Role |
|---------|------|
| `edge-tts` | Primary TTS — Microsoft neural voices, free, cloud, ~0 RAM |
| `miniaudio` | Decodes edge-tts MP3 output to PCM for playback |
| `sounddevice` | Audio playback |
| `cffi` | sounddevice's C backend (not auto-installed by pip) |
| `kokoro-onnx` | Optional offline fallback — activates if edge-tts fails |
| `onnxruntime` | ONNX runtime (auto-installed with kokoro-onnx) |

**Engine priority:** edge-tts (primary) → kokoro-onnx (fallback, if installed)

---

## Install

### Option A — npx (recommended)

```bash
# Install for current project only (skill + settings.local.json in ./.claude/)
npx @domdhi/claude-code-tts

# Install globally (skill + settings.json in ~/.claude/, all projects)
npx @domdhi/claude-code-tts --global
```

Requires Node.js 16+ and Python 3.10+. No cloning required.

The installer automatically:
1. Checks Python version (3.10+ required)
2. Installs required packages (`edge-tts`, `miniaudio`, `sounddevice`, `cffi`)
3. Copies hook scripts to the install directory (`.claude/hooks/tts/` locally, `~/.claude/hooks/tts/` globally)
4. Creates the `on` file (TTS enabled immediately)
5. Optionally installs kokoro-onnx offline fallback (~340MB, models stored globally at `~/.claude/hooks/tts/models/`)
6. Installs the `/voice` skill to `.claude/skills/voice/`
7. Patches `settings.local.json` / `settings.json` with hook entries and status line (backs up original first)
8. Detects and replaces stale TTS hooks from previous installs — safe to reinstall without duplicates

**Local vs global:**
- Default (no flag): everything goes into `./.claude/` — hook scripts, skill, and `settings.local.json` (gitignored). Good for shipping TTS config alongside a project. Each install gets its own daemon port, so multiple local-installed projects run independently without conflict.
- `--global`: everything goes into `~/.claude/` — hook scripts, skill, and `settings.json`. Recommended for personal use across all projects.

### Option B — installer script

```bash
git clone https://github.com/Domdhi/claude-code-tts
cd claude-code-tts
pip install edge-tts miniaudio sounddevice cffi
python install.py           # project-local
python install.py --global  # global (all projects)
```

### Option C — manual (Mac/Linux)

```bash
# Install packages
pip install edge-tts miniaudio sounddevice cffi

# Copy hook scripts
mkdir -p ~/.claude/hooks/tts
cp .claude/hooks/tts/daemon.py .claude/hooks/tts/stop.py \
   .claude/hooks/tts/task-hook.py .claude/hooks/tts/repeat.py \
   .claude/hooks/tts/statusline.py .claude/hooks/tts/voices.json \
   ~/.claude/hooks/tts/

# Copy /voice skill
mkdir -p ~/.claude/skills/voice
cp .claude/skills/voice/*.md ~/.claude/skills/voice/

# Enable TTS
touch ~/.claude/hooks/tts/on
```

Then add the settings snippet below manually.

---

## Claude Code Settings

The installer patches this automatically. For manual setup, add to `~/.claude/settings.json` (global) or `.claude/settings.local.json` (project-local, gitignored). If you already have a `"hooks"` key, merge these entries — don't replace the whole object.

**Mac/Linux:**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$HOME/.claude/hooks/tts/stop.py\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$HOME/.claude/hooks/tts/task-hook.py\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$HOME/.claude/hooks/tts/repeat.py\""
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "python \"$HOME/.claude/hooks/tts/statusline.py\""
  }
}
```

**Windows** (replace `C:\Users\YourName` with your actual home path):
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:\\Users\\YourName\\.claude\\hooks\\tts\\stop.py\""
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:\\Users\\YourName\\.claude\\hooks\\tts\\task-hook.py\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"C:\\Users\\YourName\\.claude\\hooks\\tts\\repeat.py\""
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "python \"C:\\Users\\YourName\\.claude\\hooks\\tts\\statusline.py\""
  }
}
```

---

## Commands

Everything goes through `/voice`. Simple commands are handled instantly by the hook (no LLM roundtrip). `change` and `read` use the skill.

| Command | Effect | Handled by |
|---------|--------|-----------|
| `/voice` | Toggle TTS on/off | Hook (instant) |
| `/voice on` | Enable TTS | Hook (instant) |
| `/voice off` | Disable TTS + stop playback | Hook (instant) |
| `/voice stop` | Stop speech + disable TTS | Hook (instant) |
| `/voice repeat` | Replay last spoken response | Hook (instant) |
| `/voice change <name>` | Change voice and/or speed | Skill (LLM) |
| `/voice read <file>` | Read a file or folder aloud | Skill (LLM) |
| `/voice <name> [faster\|slower]` | Quick voice + speed shortcut | Skill (LLM) |

---

## Offline Fallback (kokoro-onnx)

kokoro-onnx is an optional local TTS engine. It activates automatically if edge-tts fails (no internet, rate limit, etc.). Models are stored globally at `~/.claude/hooks/tts/models/` and shared by all projects.

```bash
pip install kokoro-onnx

# Download model files (~340MB total)
# Mac/Linux:
mkdir -p ~/.claude/hooks/tts/models
curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" \
     -o ~/.claude/hooks/tts/models/kokoro-v1.0.onnx
curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" \
     -o ~/.claude/hooks/tts/models/voices-v1.0.bin

# Windows (PowerShell):
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\hooks\tts\models"
Invoke-WebRequest "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" `
    -OutFile "$env:USERPROFILE\.claude\hooks\tts\models\kokoro-v1.0.onnx"
Invoke-WebRequest "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" `
    -OutFile "$env:USERPROFILE\.claude\hooks\tts\models\voices-v1.0.bin"
```

The daemon searches for models in the project-local `models/` directory first, then falls back to the global location.

---

## Voice Configuration

Edit `voices.json` in your hooks directory, or use `/voice change` interactively.

### Available voices

| Name | Key | Edge TTS voice | Style |
|------|-----|----------------|-------|
| Heart | `af_heart` | en-US-AriaNeural | warm, natural female (default) |
| Bella | `af_bella` | en-US-MichelleNeural | polished female |
| Sarah | `af_sarah` | en-US-SaraNeural | professional female |
| Sky | `af_sky` | en-US-JennyNeural | friendly, conversational |
| Nova | `af_nova` | en-US-MonicaNeural | energetic female |
| Michael | `am_michael` | en-US-GuyNeural | natural, authoritative male |
| Adam | `am_adam` | en-US-DavisNeural | deep male |
| Echo | `am_echo` | en-US-TonyNeural | casual male |
| Eric | `am_eric` | en-US-EricNeural | confident male |
| Liam | `am_liam` | en-US-RyanNeural | young, energetic male |
| Onyx | `am_onyx` | en-US-ChristopherNeural | deep, authoritative male |

### Voice priority (highest → lowest)

1. `[AgentName]:` prefix in response text → agent voice from `voices.json`
2. Project key match → `voices.json` `"projects"` section
3. `"default"` entry in `voices.json`

### Per-agent voices (task-hook.py)

`task-hook.py` reads `subagent_type` from the Task tool input and looks up the agent by name:

```json
{
  "default": {"voice": "af_heart", "speed": 1.0},
  "general-purpose": {"voice": "am_michael", "speed": 1.0},
  "code-reviewer": {"voice": "am_onyx", "speed": 0.9}
}
```

### Per-agent prefix (stop.py)

Any agent that begins its response with `[AgentName]:` gets routed to that voice. Add to the agent's system prompt:
```
Always begin your response with [AgentName]:
```
Add to `voices.json`:
```json
{
  "MyAgent": {"voice": "am_adam", "speed": 0.9}
}
```
The hook strips `[AgentName]:` before speaking.

### Per-project voices

Add a `"projects"` section. Keys are matched as case-insensitive substrings of the encoded project path under `~/.claude/projects/`:

```bash
ls ~/.claude/projects/   # shows encoded dir names like c--Users-me-Repos-MyProject
```

```json
{
  "projects": {
    "MyProject": {"voice": "am_onyx", "speed": 0.95},
    "another-repo": {"voice": "af_sarah", "speed": 1.0}
  }
}
```

---

## Enable / Disable

Use `/voice on`, `/voice off`, or `/voice` (toggle) in Claude Code. These are instant (hook-based).

The underlying mechanism is the presence of the `on` file in the hooks directory. You can also toggle manually:

```bash
# Disable
rm ~/.claude/hooks/tts/on

# Re-enable
touch ~/.claude/hooks/tts/on          # Mac/Linux
echo. > %USERPROFILE%\.claude\hooks\tts\on  # Windows cmd
```

---

## Status Line

The installer configures a status line that shows `TTS on | Nova` or `TTS off` at the bottom of Claude Code. If you already have a status line configured, the installer chains to it — your existing status line output appears first, with TTS status appended.

The status line updates after each assistant message. Hook-only commands (on/off/stop) display feedback in the blocked-by-hook message and the status line catches up on the next response.

---

## Daemon Protocol

The daemon runs on `localhost` on a port derived from the install directory (range 49152–65535). Each install location gets a stable, unique port — so multiple local-installed projects run independent daemons without conflict. Hook scripts and the daemon compute the same port, so they always find each other.

Accepts JSON lines:

| Command | Effect |
|---------|--------|
| `{"cmd": "speak", "text": "...", "voice": "af_heart", "speed": 1.0, "project": "repo"}` | Queue speech |
| `{"cmd": "stop"}` | Stop immediately, clear queue |
| `{"cmd": "ping"}` | Health check → `{"ok": true, "pid": N}` |
| `{"cmd": "quit"}` | Shut down daemon |

**Queue behavior:** at most one item per `project` key. New message from the same project replaces its queued slot. Messages from different projects line up. Omit `project` for single-project use.

---

## Performance Tuning

The daemon runs at below-normal process priority and limits ONNX threads by default. To adjust:

```python
# Top of daemon.py, before any imports
os.environ.setdefault('OMP_NUM_THREADS', '4')         # lower = less CPU spike
os.environ.setdefault('ONNXRUNTIME_NUM_THREADS', '4') # higher = faster synthesis
```

After editing daemon.py, restart the daemon:
```bash
# Mac/Linux
pkill -f daemon.py

# Windows (kills all Python processes — close other Python apps first)
taskkill /F /IM python.exe
```
The daemon auto-restarts on the next Claude response.

---

## Troubleshooting

### No audio output
- Check that the `on` file exists: `ls ~/.claude/hooks/tts/on`
- Check that settings.json hooks are wired correctly
- Check `~/.claude/hooks/tts/daemon.log` for errors

### edge-tts fails silently
- Requires internet access — check connectivity
- If offline, install kokoro-onnx fallback (see above)
- Check `~/.claude/hooks/tts/debug.log` for synthesis errors

### kokoro-onnx not found at startup
- This is expected if you skipped the offline fallback install
- The daemon will log: `kokoro-onnx not installed — edge-tts only`
- Install it if you need offline support: `pip install kokoro-onnx` + download models
- The daemon checks both project-local and global (`~/.claude/hooks/tts/models/`) model directories

### cffi not found / sounddevice import error
- Run: `pip install cffi`
- sounddevice doesn't always pull in cffi automatically

### Daemon keeps restarting / won't stay up
- Each install uses a unique port derived from its directory path — port conflicts between installs are not possible
- Check `daemon.log` in your hooks directory for errors

### Audio cuts off mid-sentence (kokoro fallback)
- kokoro-onnx has a 510-token (~1500 char) hard limit
- The daemon chunks text at sentence boundaries automatically — if you're hitting this, check `debug.log` for `IndexError`

### Duplicate speech on responses
- Check for both global and project-local hooks firing — run the installer to clean up stale hooks, or remove the global install with `rm -rf ~/.claude/hooks/tts` and remove TTS entries from `~/.claude/settings.json`

### Windows: hook command not found / `C:Python313python.exe`
- Claude Code runs hooks via bash, which cannot resolve `C:\...\python.exe` as a command
- Hook commands must use `python` (on PATH), not the full Windows executable path
- The installer handles this automatically; for manual edits use `python "C:\...\script.py"` not `C:\Python313\python.exe "C:\...\script.py"`

### Windows: DETACHED_PROCESS causes silence
- Do not add `DETACHED_PROCESS` to the subprocess flags — it breaks the Windows audio session
- `CREATE_NO_WINDOW` only is correct (already set in the hook files)
