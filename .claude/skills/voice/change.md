Change the default TTS voice and/or speed. The user may provide exact names, natural language descriptions, or both.

## Steps

1. Read the voices.json file to find the current default voice and speed. Check both locations:
   - ./.claude/hooks/tts/voices.json (project-local, check first)
   - ~/.claude/hooks/tts/voices.json (global fallback)

2. Parse $ARGUMENTS. The argument can be:
   - A voice name or alias: "onyx", "Heart", "am_adam"
   - A speed modifier: "faster", "slower", "speed 1.2", "1.5x"
   - A natural language description: "bubbly girl", "deep authoritative male", "make it faster", "calm female voice"
   - Any combination of the above: "nova faster", "deep male voice at 0.9 speed"
   - Empty (no args) — go to interactive mode (step 3)

   **Speed parsing:**
   - "faster" / "speed up" → current speed + 0.15
   - "slower" / "slow down" → current speed - 0.15
   - "fast" → 1.2
   - "slow" → 0.85
   - "normal speed" / "default speed" / "reset speed" → 1.0
   - An explicit number like "1.3", "0.9", "1.5x", "speed 1.1" → use that value
   - Clamp final speed to range 0.5–2.0

   **Natural language voice matching** — map descriptions to the best-fit voice:
   - warm, natural, gentle, kind → Heart
   - polished, smooth, elegant, refined → Bella
   - professional, clear, crisp, formal → Sarah
   - friendly, conversational, casual (female) → Sky
   - energetic, bright, bubbly, perky, upbeat (female) → Nova
   - natural, authoritative, confident (male) → Michael
   - deep, resonant, rich, low (male) → Adam
   - casual, relaxed, chill, laid-back (male) → Echo
   - confident, direct, bold (male) → Eric
   - young, energetic, upbeat (male) → Liam
   - deep, authoritative, commanding, powerful (male) → Onyx

   If only speed is being changed (no voice specified), keep the current voice.
   If only voice is being changed (no speed specified), keep the current speed.

3. **Interactive mode** (only when $ARGUMENTS is empty):

   Show the user a table with friendly names and mark the current default:

   | Name | Style | Gender |
   |------|-------|--------|
   | Heart | Warm, natural | Female |
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

   Then use AskUserQuestion in two rounds:

   First — group:
   - "Female voices" (description: "Heart, Bella, Sarah, Sky, Nova")
   - "Male voices" (description: "Michael, Adam, Echo, Eric, Liam, Onyx")

   Second — pick voice using friendly names as labels, style as description:
   Female: Heart (Warm, natural), Bella (Polished, smooth), Sky (Friendly, conversational), Nova (Energetic, bright)
   Male: Michael (Natural, authoritative), Adam (Deep, resonant), Echo (Casual, relaxed), Onyx (Deep, authoritative)

4. Resolve the chosen voice to its full key using the alias table, then update voices.json. Use the Edit tool — change "voice" and/or "speed" in the "default" block. Preserve everything else.

5. Respond with a short confirmation like: "Voice changed to Nova at 1.2x speed." — TTS will speak it.

## Alias table

Match case-insensitively → resolve to full key for voices.json:

| Aliases | Key |
|---------|-----|
| heart, af_heart | af_heart |
| bella, af_bella | af_bella |
| sarah, af_sarah | af_sarah |
| sky, af_sky | af_sky |
| nova, af_nova | af_nova |
| michael, am_michael | am_michael |
| adam, am_adam | am_adam |
| echo, am_echo | am_echo |
| eric, am_eric | am_eric |
| liam, am_liam | am_liam |
| onyx, am_onyx | am_onyx |

If the argument doesn't match any voice or description, respond with: "I couldn't match that to a voice. Use /voice:change to browse them interactively."

Target: $ARGUMENTS
