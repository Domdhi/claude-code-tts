#!/usr/bin/env python3
"""claude-code-tts — Status line script.
Appends TTS state and voice to the Claude Code status bar.
Chains to any pre-existing statusLine command so we never clobber the user's setup.

Receives session JSON on stdin; outputs status string(s) on stdout.
"""

import json
import os
import subprocess
import sys

_home_hooks = os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'tts')

# File written by install.py with the original statusLine command (if any)
_CHAIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statusline_chain.txt')

# Friendly display names for voice keys
_VOICE_NAMES = {
    'af_heart': 'Heart', 'af_bella': 'Bella', 'af_sarah': 'Sarah',
    'af_sky': 'Sky', 'af_nova': 'Nova',
    'am_michael': 'Michael', 'am_adam': 'Adam', 'am_echo': 'Echo',
    'am_eric': 'Eric', 'am_liam': 'Liam', 'am_onyx': 'Onyx',
    'bf_sonia': 'Sonia', 'bf_maisie': 'Maisie',
    'bm_ryan': 'Ryan', 'bm_thomas': 'Thomas',
    'xf_natasha': 'Natasha', 'xm_william': 'William',
    'if_neerja': 'Neerja', 'im_prabhat': 'Prabhat',
    'ef_emily': 'Emily', 'em_connor': 'Connor',
}


def _find_hook_dir():
    """Return the first hook dir that exists (project-local first, then global)."""
    cwd_hooks = os.path.join(os.getcwd(), '.claude', 'hooks', 'tts')
    for d in (cwd_hooks, _home_hooks):
        if os.path.isdir(d):
            return d
    return None


def _run_chained(stdin_data):
    """Run the original statusLine command and return its output."""
    if not os.path.exists(_CHAIN_FILE):
        return ''
    try:
        with open(_CHAIN_FILE, 'r', encoding='utf-8') as f:
            cmd = f.read().strip()
        if not cmd:
            return ''
        result = subprocess.run(
            cmd, shell=True, input=stdin_data,
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.rstrip('\n')
    except Exception:
        return ''


def main():
    # Read stdin once — pass it to chained command and use for our own logic
    try:
        stdin_data = sys.stdin.read()
    except Exception:
        stdin_data = ''

    # Run any chained (pre-existing) statusline command first
    chained_output = _run_chained(stdin_data)

    hook_dir = _find_hook_dir()
    if not hook_dir:
        # No TTS installed — just pass through chained output
        if chained_output:
            print(chained_output)
        return

    on = os.path.exists(os.path.join(hook_dir, 'on'))

    voice = 'af_heart'
    voices_file = os.path.join(hook_dir, 'voices.json')
    voices_cfg = {}
    try:
        with open(voices_file, 'r', encoding='utf-8') as f:
            voices_cfg = json.load(f)
            voice = voices_cfg.get('default', {}).get('voice', voice)
    except Exception:
        pass

    # If session_pool is active, show the pool-assigned voice for this session
    sessions_file = os.path.join(hook_dir, 'sessions.json')
    if voices_cfg.get('session_pool'):
        try:
            session_data = json.loads(stdin_data) if stdin_data else {}
            sid = session_data.get('session_id', '')
            if not sid:
                tp = session_data.get('transcript_path', '')
                if tp:
                    sid = os.path.splitext(os.path.basename(tp))[0]
            if sid:
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
                if sid in sessions:
                    voice = sessions[sid].get('voice', voice)
        except Exception:
            pass

    display_name = _VOICE_NAMES.get(voice, voice)
    tts_status = f'TTS on | {display_name}' if on else 'TTS off'

    if chained_output:
        print(f'{chained_output} | {tts_status}')
    else:
        print(tts_status)


if __name__ == '__main__':
    main()
