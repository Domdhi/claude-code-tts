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

Requires Node.js 16+ and Python 3.10+. The installer handles everything else: Python packages, hook scripts, the `/voice` skill, status line, and settings — one command, no build tools. It also offers optional setup for:

- **Offline fallback** (kokoro-onnx) — local TTS when you're offline
- **Session pool** — auto-assign unique voices when running multiple CC instances
- **CLAUDE.md snippet** — makes Claude write spoken prose instead of markdown when voice is active

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
| `/voice stop` | Stop current speech |
| `/voice repeat` | Replay last response |
| `/voice read <file>` | Read a file or folder aloud |
| `/voice change <name>` | Change voice (e.g. `onyx`, `heart`, `nova`) |
| `/voice <name> [faster\|slower]` | Quick voice + speed change |

Simple commands (`on`/`off`/`stop`/`repeat`/toggle) are handled instantly by the hook — no LLM roundtrip. `change` and `read` use the skill for natural language processing.

---

## Voices

21 built-in voices — 11 American + 10 accent voices. Use `/voice change` interactively or `/voice change <name>` directly:

**American**

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

**Accents**

| Name | Accent | Style | Gender |
|------|--------|-------|--------|
| Sonia | British | Warm, polished | Female |
| Maisie | British | Young, cheerful | Female |
| Ryan | British | Balanced, clear | Male |
| Thomas | British | Refined, distinguished | Male |
| Natasha | Australian | Friendly, natural | Female |
| William | Australian | Confident, warm | Male |
| Neerja | Indian | Expressive, warm | Female |
| Prabhat | Indian | Clear, professional | Male |
| Emily | Irish | Soft, melodic | Female |
| Connor | Irish | Warm, natural | Male |

Natural language works too: `/voice bubbly girl faster` or `/voice british male` or `/voice australian`

**Need more?** Edge TTS has 48+ English voices across 14 locales. Add any Edge TTS voice directly to `voices.json` — see [INSTALL.md](INSTALL.md#custom-edge-tts-voices) for details.

**Per-agent**, **per-project**, and **per-session** voice routing via `voices.json` — see [INSTALL.md](INSTALL.md) for details. Running multiple CC instances? Add a `session_pool` and each instance gets its own voice automatically.

---

## TTS-Optimized Responses

By default, the hooks strip markdown before reading — but code blocks become `[code block]` and tables turn to mush. For better results, tell Claude to write spoken prose when voice is active.

The installer ships a ready-to-paste `CLAUDE.md` snippet at `.claude/hooks/tts/CLAUDE_SNIPPET.md`. Add it to your project's `CLAUDE.md`:

```bash
cat .claude/hooks/tts/CLAUDE_SNIPPET.md >> CLAUDE.md
```

With this, Claude detects voice mode and writes flowing sentences instead of bullet-heavy markdown. Code blocks still work for actual code — only the explanatory text changes.

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
