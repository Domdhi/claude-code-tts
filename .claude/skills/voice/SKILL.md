---
name: voice
description: "TTS voice control — toggle auto-read, change voice/speed, read files aloud, stop/repeat speech"
---

# /voice

TTS voice control. Simple commands (on/off/stop/repeat/toggle) are handled instantly by the hook — they never reach here. This skill only handles commands that need the LLM.

| Command | Handled by |
|---------|-----------|
| `/voice` (no args) | Hook (toggle) |
| `/voice on` / `/voice off` | Hook |
| `/voice stop` | Hook |
| `/voice repeat` | Hook |
| `/voice change [voice/description]` | This skill → `change.md` |
| `/voice read [file/folder]` | This skill → `read.md` |
| `/voice <name> [faster/slower]` | This skill → `change.md` |

## Routing

Parse the **first word** of `$ARGUMENTS` (case-insensitive):

- **`change`** → Strip the first word, pass the rest as the target. Follow instructions in `change.md`
- **`read`** → Strip the first word, pass the rest as the file/folder path. Follow instructions in `read.md`
- **Anything else** → Assume it's a voice name or natural language description for `change.md` (e.g. `/voice onyx` or `/voice bubbly girl faster`)

## Arguments

$ARGUMENTS
