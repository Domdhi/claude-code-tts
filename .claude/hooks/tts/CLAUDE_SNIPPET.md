## Voice Mode (TTS)

When TTS auto-read is active (`/voice on`), format responses for spoken output:

- Write in flowing sentences and paragraphs — not bullet lists or tables
- Describe code changes conversationally ("I updated the auth middleware to check token expiry before validating the signature") rather than dumping raw diffs
- Code blocks are still fine when writing/editing actual code — but explanatory text around them should be speakable
- No emoji, no ASCII art, no deeply nested markdown
- Keep it concise — spoken output shouldn't ramble

When voice is off, use normal markdown formatting.

Detection: `test -f .claude/hooks/tts/on && echo "voice:on" || echo "voice:off"`
