Read a file or folder aloud via TTS. Your entire response will be spoken by the TTS system, so write in plain, speakable prose — no markdown formatting, no code blocks, no bullet points.

## Target

$ARGUMENTS

## Instructions

1. Determine the target:
   - If a path is provided in the Target section above, use it.
   - If the target is empty, look through this conversation for the last file that was created, written, or edited (via Write, Edit, or NotebookEdit tools). Use that file path.
   - If no file was touched in this conversation, respond with only: "No file specified and I couldn't find a recently edited file in our conversation."

2. Read the target:
   - If it's a single file, use the Read tool to get its contents.
   - If it's a directory, use the Bash tool to run ls on it, then describe what's there.

3. Present the contents for speech. Adapt based on file type:
   - Text and documentation files (README, .md, .txt, etc.): Read the content naturally, converting any markup to plain spoken language.
   - Code files (.py, .js, .ts, etc.): Describe the file's purpose, then walk through its structure — imports, key classes, functions with their signatures and what they do. Don't read raw code syntax verbatim.
   - Config files (JSON, YAML, TOML, .env, etc.): Summarize the key settings and their values in plain language.
   - For directories: Describe the folder's organization — file names, types, and what the structure suggests.

4. Formatting rules for your response (critical — this will be read aloud):
   - Write in flowing sentences and paragraphs only.
   - No markdown: no headers, bold, italic, backticks, code blocks, or link syntax.
   - No bullet points or numbered lists.
   - No tables or diagrams.
   - Keep it concise. Aim for a natural, spoken summary — as if you were explaining the file to someone on a call.
