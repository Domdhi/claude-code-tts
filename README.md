# claude-code-tts

Neural TTS hook system for [Claude Code](https://claude.ai/code). Reads Claude's responses aloud as they finish.

**Engines:** Edge TTS (Microsoft neural voices, free, requires internet) with automatic offline fallback to kokoro-onnx.
**Platform:** Windows, macOS, Linux
**Install:** one command, no build tools required

---

## Quick Start

```bash
# Install for current project only
npx @domdhi/claude-code-tts

# Install globally (all projects)
npx @domdhi/claude-code-tts --global
```

That's it. The installer copies the hook files into `.claude/hooks/tts/`, enables TTS, optionally installs the offline fallback, installs slash commands, and patches `settings.local.json` — all in the current project directory. Use `--global` to install once for all projects.

**Requirements:** Node.js 16+ and Python 3.10+ must both be installed. The hooks run in Python — Node is only used for the install command.

**Or install manually:**
```bash
git clone https://github.com/Domdhi/claude-code-tts
cd claude-code-tts
pip install edge-tts miniaudio sounddevice cffi
python install.py           # project-local
python install.py --global  # all projects
```

---

## What It Does

Three Claude Code hooks work together:

| Hook | File | When it fires |
|------|------|---------------|
| `Stop` | `stop.py` | After every Claude response — reads it aloud |
| `PostToolUse:Task` | `task-hook.py` | After a subagent finishes — reads its output |
| `UserPromptSubmit` | `repeat.py` | On `/voice:repeat` or `/voice:stop` commands |

A persistent daemon (`daemon.py`) keeps the TTS model loaded in the background. Hook files connect to it via TCP on `localhost:6254`, starting it automatically if needed.

---

## Voice Configuration

Edit `~/.claude/hooks/tts/voices.json` to customize voices per agent or per project.

**Available voices:**

| Key | Edge TTS | Style |
|-----|----------|-------|
| `af_heart` | AriaNeural | warm female (default) |
| `af_bella` | MichelleNeural | polished female |
| `af_sarah` | SaraNeural | professional female |
| `af_sky` | JennyNeural | friendly female |
| `af_nova` | MonicaNeural | energetic female |
| `am_michael` | GuyNeural | natural male |
| `am_adam` | DavisNeural | deep male |
| `am_echo` | TonyNeural | casual male |
| `am_eric` | EricNeural | confident male |
| `am_liam` | RyanNeural | energetic male |
| `am_onyx` | ChristopherNeural | authoritative male |

**Per-agent voices** — `task-hook.py` reads `subagent_type` from the Task tool and looks up the agent by name:
```json
{
  "default": {"voice": "af_heart", "speed": 1.0},
  "general-purpose": {"voice": "am_michael", "speed": 1.0}
}
```

**Per-project voices** — add a `"projects"` section with keys matched against the project path:
```json
{
  "projects": {
    "my-project": {"voice": "am_onyx", "speed": 0.95}
  }
}
```

**Per-agent prefix** — add `Always begin your response with [AgentName]:` to an agent's system prompt, then add it to `voices.json`:
```json
{
  "MyAgent": {"voice": "am_adam", "speed": 0.9}
}
```
The hook strips the `[AgentName]:` prefix before speaking.

See [INSTALL.md](INSTALL.md) for the full configuration reference.

---

## Commands

Type these in the Claude Code prompt:

| Command | Effect |
|---------|--------|
| `/voice:stop` | Stop speech immediately |
| `/voice:repeat` | Replay last response |
| `/voice:on` | Re-enable TTS |
| `/voice:off` | Disable TTS |

---

## Enable / Disable

TTS is controlled by the presence of an `on` file in the install directory:

```bash
# Disable
rm ~/.claude/hooks/tts/on

# Re-enable (Mac/Linux)
touch ~/.claude/hooks/tts/on

# Re-enable (Windows cmd)
echo. > %USERPROFILE%\.claude\hooks\tts\on
```

---

## Requirements

- Python 3.10+
- Node.js 16+ (for `npx` install only)
- Claude Code
- Internet connection (for Edge TTS primary engine)
- `edge-tts`, `miniaudio`, `sounddevice`, `cffi` (installed automatically)
- Optional: `kokoro-onnx` + model files (~82MB) for offline fallback

---

## License

MIT — see [LICENSE](LICENSE)
