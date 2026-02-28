# Changelog

All notable changes to claude-code-tts are documented here.

## [Unreleased] — 2026-02-28

### Added
- **/voice skill** — single `/voice` command with args-based routing replaces individual `/voice:*` commands
  - `/voice change <name|description>` — change voice and/or speed with aliases (`onyx`, `heart`) and natural language (`bubbly girl faster`)
  - `/voice read <file|folder>` — read a file or folder aloud, context-aware (auto-detects last edited file)
  - `/voice on` / `/voice off` / `/voice` (toggle) — handled instantly by hook, no LLM roundtrip
  - `/voice stop` — stops current speech (TTS stays enabled)
  - `/voice repeat` — replays last spoken response
- **10 accent voices** — British (Sonia, Maisie, Ryan, Thomas), Australian (Natasha, William), Indian (Neerja, Prabhat), Irish (Emily, Connor)
- **Custom Edge TTS voice passthrough** — use any Edge TTS `ShortName` directly in `voices.json` (e.g. `en-SG-LunaNeural`)
- **Status line integration** — shows `TTS on | Nova` or `TTS off` in the Claude Code status bar
  - Friendly voice names (Nova, Onyx, Heart) instead of raw keys (af_nova, am_onyx)
  - Chains to any existing statusLine command — never clobbers user setup
- **Hook-based on/off/toggle** — instant execution via UserPromptSubmit hook, no LLM needed
  - Block reason messages provide feedback: "TTS enabled. Status line updates on next message."
- **Reinstall safety** — installer detects and replaces stale TTS hooks from previous install paths instead of duplicating them

### Changed
- **Installer: commands → skills** — installs to `.claude/skills/voice/` instead of `.claude/commands/voice/`
- **Kokoro models install globally** — `~/.claude/hooks/tts/models/` shared by all projects, no per-project duplication
  - Daemon searches local then global models dir
  - Installer messaging clarified: "Models install once to ~/.claude/hooks/tts/models and are shared by all projects"
- **`/voice stop` stops speech only** — no longer disables TTS; use `/voice off` to disable
- **Fixed model size in docs** — corrected ~82MB → ~340MB (311MB model + 27MB voices)

### Removed
- **`on.md` / `off.md` command files** — replaced by hook-based toggle in `repeat.py`
- **`auto-read.md` / `stop.md` / `repeat.md` skill files** — handled entirely by hook, no skill routing needed

## [2.0.4] — 2026-02-28

### Fixed
- Write hooks `.gitignore` inline in installer — npm hardcodes dotfiles as always-excluded from packages, overriding the `files` array; inline write is the only reliable solution

## [2.0.3] — 2026-02-28

### Fixed
- Explicitly list `.claude/hooks/tts/.gitignore` in `package.json` files array (later found insufficient — npm's dotfile exclusion overrides `files` regardless)

## [2.0.2] — 2026-02-28

### Added
- `.gitignore` inside the hooks install directory — suppresses runtime state files (`on`, `last.txt`, `daemon.log`, `pid`, `models/`) from appearing in `git status` for local installs

## [2.0.1] — 2026-02-28

### Fixed
- `/voice:off` now sends a stop command to the daemon before removing the `on` file — previously, currently-playing audio would finish before going silent
- Stop command targets both global (`~/.claude/hooks/tts`) and project-local (`./.claude/hooks/tts`) daemons

## [2.0.0] — 2026-02-27

### Added
- Initial release as standalone npm package (`@domdhi/claude-code-tts`)
- Edge TTS as primary engine (Microsoft neural voices, cloud)
- Kokoro-onnx as offline fallback engine
- 11 voice options across male and female with personality-matched Edge TTS mapping
- Per-project and per-agent voice routing via `voices.json`
- Daemon architecture with TCP protocol for responsive playback
- Project-local and global install modes
- Automatic daemon lifecycle (starts on first speak, responds to quit)
- Markdown stripping and unicode sanitization for clean speech output
- `/voice:on`, `/voice:off`, `/voice:stop`, `/voice:repeat` slash commands
- Queue management: one pending item per project, new messages replace queued

### Pre-2.0 History

Originally developed as VoiceOut, a personal tool inside the Domdhi.Cockpit project. Extracted to standalone repo for npm publishing.

## [1.1.0] — 2026-02-26

### Changed (VoiceOut v2 — Neural TTS)
- Replaced Windows SAPI engine with kokoro-onnx neural TTS — natural, expressive voices vs. robotic SAPI
- Replaced per-speak model load with persistent background daemon — kokoro pipeline stays loaded in memory (~2s cold start, instant after)
- Daemon queues audio across multiple Claude Code sessions — prevents simultaneous sessions from colliding on the audio device
- Added `voices.json` for per-agent voice mapping — agents prefix output with `[AgentName]:`, hook strips prefix and looks up voice

### Fixed
- Multi-instance audio collision — multiple Claude Code windows previously talked over each other; daemon serializes all output

## [1.0.0] — 2026-02-26

### Added (VoiceOut v1 — Windows SAPI)
- `Stop` hook (`stop.py`) — reads Claude's transcript after every response, speaks last assistant message via Windows SAPI (PowerShell `System.Speech.Synthesis`)
- `UserPromptSubmit` hook (`repeat.py`) — intercepts `/voice:repeat` and `/voice:stop` without LLM roundtrip
- `on` flag file — TTS active only when file exists; delete to disable silently
- `last.txt` — persists last spoken text for `/voice:repeat`
- `pid` tracking — kills active speech process on new response, enabling true `/voice:stop`
- `/voice:on`, `/voice:off`, `/voice:repeat`, `/voice:stop` slash commands
- `READ_ALL_CHAIN` flag — reads entire tool-use chain when `True`, last message only when `False`
