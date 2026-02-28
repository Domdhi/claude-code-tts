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

Requires Node.js 16+ and Python 3.10+. The installer handles everything else: Python packages, hook scripts, the `/voice` skill, status line, and settings — one command, no build tools.

---

## How It Works

Three Claude Code hooks wire into the response lifecycle:

| Hook | Fires when | File |
|------|------------|------|
| `Stop` | Claude finishes any response | `stop.py` |
| `PostToolUse:Task` | A subagent completes | `task-hook.py` |
| `UserPromptSubmit` | You type `/voice` commands | `repeat.py` |

A persistent background daemon (`daemon.py`) keeps the TTS model warm. Hook scripts connect to it over TCP on localhost — it starts automatically on the first response and stays running between turns.

**Engine priority:** Edge TTS (Microsoft neural voices, free, cloud) → kokoro-onnx (local fallback, activates automatically if Edge TTS fails or you're offline)

**Status line** shows TTS state and current voice at the bottom of Claude Code (e.g. `TTS on | Nova`).

---

## Commands

Everything goes through `/voice`:

| Command | Effect |
|---------|--------|
| `/voice` | Toggle TTS on/off |
| `/voice on` | Enable TTS |
| `/voice off` | Disable TTS and stop playback |
| `/voice stop` | Stop speech and disable TTS |
| `/voice repeat` | Replay last response |
| `/voice read <file>` | Read a file or folder aloud |
| `/voice change <name>` | Change voice (e.g. `onyx`, `heart`, `nova`) |
| `/voice <name> [faster\|slower]` | Quick voice + speed change |

Simple commands (`on`/`off`/`stop`/`repeat`/toggle) are handled instantly by the hook — no LLM roundtrip. `change` and `read` use the skill for natural language processing.

---

## Voices

11 voices with friendly aliases. Use `/voice change` interactively or `/voice change <name>` directly:

| Name | Style | Gender |
|------|-------|--------|
| Heart | Warm, natural *(default)* | Female |
| Bella | Polished, smooth | Female |
| Sarah | Professional, clear | Female |
| Sky | Friendly, conversational | Female |
| Nova | Energetic, bright | Female |
| Michael | Natural, authoritative | Male |
| Adam | Deep, resonant | Male |
| Echo | Casual, relaxed | Male |
| Eric | Confident, direct | Male |
| Liam | Young, energetic | Male |
| Onyx | Deep, authoritative | Male |

Natural language works too: `/voice bubbly girl faster` or `/voice deep authoritative male at 0.9 speed`

**Per-agent** and **per-project** voice routing via `voices.json` — see [INSTALL.md](INSTALL.md) for details.

---

## Offline Fallback

kokoro-onnx is an optional local engine that kicks in automatically when Edge TTS is unavailable. Models install once globally (~340MB) and are shared by all projects:

```bash
pip install kokoro-onnx
```

See [INSTALL.md](INSTALL.md) for model download steps. The daemon detects it automatically; no config change needed.

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

[CHANGELOG.md](CHANGELOG.md) tracks all changes.

---

## License

MIT — see [LICENSE](LICENSE)
