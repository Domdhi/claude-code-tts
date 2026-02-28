# claude-code-tts

[![npm](https://img.shields.io/npm/v/@domdhi/claude-code-tts)](https://www.npmjs.com/package/@domdhi/claude-code-tts)
[![npm downloads](https://img.shields.io/npm/dm/@domdhi/claude-code-tts)](https://www.npmjs.com/package/@domdhi/claude-code-tts)
[![license](https://img.shields.io/badge/license-MIT-blue)](#license)
[![platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey)](#requirements)
[![python](https://img.shields.io/badge/python-3.10%2B-blue)](#requirements)

> Claude finishes a response. Your speakers read it aloud.

Neural TTS hook system for [Claude Code](https://claude.ai/code). Hands-free — no copy-paste, no screen-watching. Just code and listen.

---

## Install

```bash
# Project-local (recommended)
npx @domdhi/claude-code-tts

# Global — all projects
npx @domdhi/claude-code-tts --global
```

Requires Node.js 16+ and Python 3.10+. The installer handles everything else: Python packages, hook scripts, slash commands, and settings — one command, no build tools.

---

## How It Works

Three Claude Code hooks wire into the response lifecycle:

| Hook | Fires when | File |
|------|------------|------|
| `Stop` | Claude finishes any response | `stop.py` |
| `PostToolUse:Task` | A subagent completes | `task-hook.py` |
| `UserPromptSubmit` | You type `/voice:stop` or `/voice:repeat` | `repeat.py` |

A persistent background daemon (`daemon.py`) keeps the TTS model warm. Hook scripts connect to it over TCP on localhost — it starts automatically on the first response and stays running between turns.

**Engine priority:** Edge TTS (Microsoft neural voices, free, cloud) → kokoro-onnx (local fallback, activates automatically if Edge TTS fails or you're offline)

---

## Voices

Edit `voices.json` in your install directory to assign voices per agent or per project.

| Key | Voice | Style |
|-----|-------|-------|
| `af_heart` | AriaNeural | warm female *(default)* |
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

**Per-agent** — assign a different voice to each subagent type:
```json
{
  "default":         { "voice": "af_heart",   "speed": 1.0 },
  "general-purpose": { "voice": "am_michael",  "speed": 1.0 },
  "code-reviewer":   { "voice": "am_onyx",     "speed": 0.9 }
}
```

**Per-project** — matched against the project path:
```json
{
  "projects": {
    "my-api": { "voice": "am_onyx", "speed": 0.95 }
  }
}
```

**Per-agent prefix** — add `Always begin your response with [AgentName]:` to a custom agent's system prompt, then add it to `voices.json`:
```json
{
  "Reviewer": { "voice": "am_adam", "speed": 0.9 }
}
```

---

## Commands

Type any of these directly in the Claude Code prompt:

| Command | Effect |
|---------|--------|
| `/voice:stop` | Stop speech immediately, clear queue |
| `/voice:repeat` | Replay last response |
| `/voice:on` | Re-enable TTS |
| `/voice:off` | Disable TTS and stop current playback |

---

## Offline Fallback

kokoro-onnx is an optional local engine that kicks in automatically when Edge TTS is unavailable (no internet, rate limit, etc.). Install it once:

```bash
pip install kokoro-onnx
```

Then download the model files (~82MB) — see [INSTALL.md](INSTALL.md) for the full steps. The daemon detects it automatically; no config change needed.

---

## Requirements

- **Claude Code** (obviously)
- **Python 3.10+** — hooks run in Python
- **Node.js 16+** — only needed for `npx` install
- **Internet** — for Edge TTS primary engine (or install the offline fallback)
- Python packages: `edge-tts`, `miniaudio`, `sounddevice`, `cffi` *(installed automatically)*

---

## Full Docs

[INSTALL.md](INSTALL.md) covers manual install, all settings, voice priority rules, daemon protocol, performance tuning, and troubleshooting.

---

## License

MIT — see [LICENSE](LICENSE)
