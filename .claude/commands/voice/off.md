Disable TTS voice output by removing the enable file. Run the appropriate command for your OS silently using the Bash tool, then respond with only: "TTS disabled."

Mac/Linux:
rm -f ~/.claude/hooks/tts/on

Windows:
del /F "%USERPROFILE%\.claude\hooks\tts\on" 2>nul
