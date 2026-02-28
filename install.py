#!/usr/bin/env python3
"""
claude-code-tts installer
Copies hook files to ~/.claude/hooks/tts/, installs the /voice skill, and patches settings.json.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys


REQUIRED_PACKAGES = ['edge-tts', 'miniaudio', 'sounddevice', 'cffi']
KOKORO_PACKAGES = ['kokoro-onnx']
KOKORO_MODEL_URLS = [
    (
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
        'kokoro-v1.0.onnx',
    ),
    (
        'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin',
        'voices-v1.0.bin',
    ),
]

# voices.json is excluded from HOOK_FILES -- handled separately to avoid clobbering customizations
HOOK_FILES = ['daemon.py', 'stop.py', 'task-hook.py', 'repeat.py', 'statusline.py']
SKILL_FILES = ['SKILL.md', 'read.md', 'change.md']

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
HOOKS_SOURCE  = os.path.join(SOURCE_DIR, '.claude', 'hooks', 'tts')
SKILL_SOURCE  = os.path.join(SOURCE_DIR, '.claude', 'skills', 'voice')

_home_claude = os.path.join(os.path.expanduser('~'), '.claude')
_proj_claude = os.path.join(os.getcwd(), '.claude')

# Default: project-local — all files go into ./.claude/ (current project)
# --global overrides all of these to ~/.claude/
INSTALL_DIR       = os.path.join(_proj_claude, 'hooks', 'tts')
MODELS_DIR        = os.path.join(INSTALL_DIR, 'models')
SKILL_INSTALL_DIR = os.path.join(_proj_claude, 'skills', 'voice')
# settings.local.json is gitignored — safe for machine-specific absolute paths
SETTINGS_FILE     = os.path.join(_proj_claude, 'settings.local.json')

GLOBAL_SCOPE = False


def step(msg):
    print(f'\n  {msg}')


def ok(msg):
    print(f'    OK  {msg}')


def warn(msg):
    print(f'    WARN  {msg}')


def fail(msg):
    print(f'    FAIL  {msg}')


def check_python():
    step('Checking Python version...')
    vi = sys.version_info
    if vi < (3, 10):
        warn(f'Python {vi.major}.{vi.minor} detected. Python 3.10+ is recommended.')
        resp = input('    Continue anyway? [y/N] ').strip().lower()
        if resp != 'y':
            sys.exit(1)
    else:
        ok(f'Python {vi.major}.{vi.minor}.{vi.micro}')


def pip_install(packages):
    cmd = [sys.executable, '-m', 'pip', 'install'] + packages
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f'pip install failed:\n{result.stderr}')
        sys.exit(1)


def install_packages():
    step(f'Installing required packages: {", ".join(REQUIRED_PACKAGES)}')
    pip_install(REQUIRED_PACKAGES)
    ok('edge-tts, miniaudio, sounddevice, cffi installed')


def create_dirs():
    step(f'Creating install directory: {INSTALL_DIR}')
    os.makedirs(INSTALL_DIR, exist_ok=True)
    ok(INSTALL_DIR)


def copy_files():
    step('Copying hook files...')
    for filename in HOOK_FILES:
        src = os.path.join(HOOKS_SOURCE, filename)
        dst = os.path.join(INSTALL_DIR, filename)
        if not os.path.exists(src):
            fail(f'Source file not found: {src}')
            sys.exit(1)
        shutil.copy2(src, dst)
        ok(filename)

    # .gitignore: written inline (npm always strips dotfiles from packages)
    gitignore_dst = os.path.join(INSTALL_DIR, '.gitignore')
    gitignore_content = (
        '# Runtime state — generated when the daemon runs, not for version control\n'
        'on\nlast.txt\ndaemon.log\ndebug.log\ntask-hook.log\npid\nmodels/\n'
        'statusline_chain.txt\n'
    )
    with open(gitignore_dst, 'w', encoding='utf-8') as f:
        f.write(gitignore_content)
    ok('.gitignore')

    # voices.json: only copy on first install -- preserve existing customizations
    voices_src = os.path.join(HOOKS_SOURCE, 'voices.json')
    voices_dst = os.path.join(INSTALL_DIR, 'voices.json')
    if os.path.exists(voices_dst):
        ok('voices.json (kept existing, not overwritten)')
    else:
        shutil.copy2(voices_src, voices_dst)
        ok('voices.json')


def copy_skill():
    step('Installing /voice skill...')
    os.makedirs(SKILL_INSTALL_DIR, exist_ok=True)
    for filename in SKILL_FILES:
        src = os.path.join(SKILL_SOURCE, filename)
        dst = os.path.join(SKILL_INSTALL_DIR, filename)
        if not os.path.exists(src):
            warn(f'Skill file not found: {src} -- skipping')
            continue
        shutil.copy2(src, dst)
        ok(filename)


def enable_tts():
    step('Enabling TTS (creating on file)...')
    on_file = os.path.join(INSTALL_DIR, 'on')
    open(on_file, 'w').close()
    ok('TTS enabled')


KOKORO_GLOBAL_MODELS = os.path.join(_home_claude, 'hooks', 'tts', 'models')


def _kokoro_already_installed():
    """True if kokoro-onnx is importable and model files exist in the global models dir."""
    import importlib.util
    if importlib.util.find_spec('kokoro_onnx') is None:
        return False
    return all(os.path.exists(os.path.join(KOKORO_GLOBAL_MODELS, f))
               for f in ('kokoro-v1.0.onnx', 'voices-v1.0.bin'))


def offer_kokoro():
    step('Offline fallback (kokoro-onnx, ~340MB download)')

    if _kokoro_already_installed():
        ok(f'kokoro-onnx already installed at {KOKORO_GLOBAL_MODELS}')
        return

    print('    Edge TTS requires internet. kokoro-onnx is a local fallback that works offline.')
    print(f'    Models install once to {KOKORO_GLOBAL_MODELS} and are shared by all projects.')
    resp = input('    Install kokoro-onnx offline fallback? [y/N] ').strip().lower()
    if resp != 'y':
        ok('Skipped (edge-tts only mode)')
        return

    step('Installing kokoro-onnx...')
    pip_install(KOKORO_PACKAGES)
    ok('kokoro-onnx installed')

    step(f'Downloading model files to {KOKORO_GLOBAL_MODELS}...')
    os.makedirs(KOKORO_GLOBAL_MODELS, exist_ok=True)
    try:
        import urllib.request
        for url, filename in KOKORO_MODEL_URLS:
            dst = os.path.join(KOKORO_GLOBAL_MODELS, filename)
            print(f'    Downloading {filename}...')
            urllib.request.urlretrieve(url, dst)
            ok(filename)
    except Exception as e:
        fail(f'Model download failed: {e}')
        print('    You can download manually -- see INSTALL.md for URLs.')


def _hook_command(script_name):
    """Return the shell command string for a given hook script."""
    path = os.path.join(INSTALL_DIR, script_name)
    if sys.platform == 'win32':
        # Claude Code runs hooks via bash — bash cannot resolve C:\...\python.exe as a command.
        # Use 'python' (on PATH) instead of the full Windows executable path.
        return f'python "{path}"'
    return f'{sys.executable} "{path}"'


def _is_tts_hook(entry):
    """Return True if a hook entry belongs to claude-code-tts (any install path)."""
    for h in entry.get('hooks', []):
        cmd = h.get('command', '')
        # Match any path ending in our script names
        if any(cmd.endswith(f'{name}"') or cmd.endswith(name)
               for name in ('stop.py', 'task-hook.py', 'repeat.py')):
            return True
    return False


def _set_hook(hooks, key, new_entry):
    """Replace any existing TTS hook entry under key, or add if none exists.
    Preserves non-TTS hooks the user may have configured."""
    entries = hooks.get(key, [])
    # Remove stale TTS hooks (e.g. from a different install path)
    cleaned = [e for e in entries if not _is_tts_hook(e)]
    cleaned.append(new_entry)
    hooks[key] = cleaned
    return len(cleaned) != len(entries)  # True if we replaced something


def patch_settings_json():
    step(f'Patching Claude Code settings: {SETTINGS_FILE}')

    stop_cmd   = _hook_command('stop.py')
    task_cmd   = _hook_command('task-hook.py')
    repeat_cmd = _hook_command('repeat.py')

    # Load existing settings (or start fresh)
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception as e:
            warn(f'Could not parse settings.json: {e}')
            warn('Skipping auto-patch. Add the hooks manually -- see INSTALL.md.')
            return

    hooks = settings.setdefault('hooks', {})
    changed = False

    # Stop hook
    replaced = _set_hook(hooks, 'Stop', {
        'hooks': [{'type': 'command', 'command': stop_cmd}]
    })
    changed = changed or replaced
    ok('Updated Stop hook' if replaced else 'Set Stop hook')

    # PostToolUse:Task hook
    replaced = _set_hook(hooks, 'PostToolUse', {
        'matcher': 'Task',
        'hooks': [{'type': 'command', 'command': task_cmd}]
    })
    changed = changed or replaced
    ok('Updated PostToolUse:Task hook' if replaced else 'Set PostToolUse:Task hook')

    # UserPromptSubmit hook
    replaced = _set_hook(hooks, 'UserPromptSubmit', {
        'hooks': [{'type': 'command', 'command': repeat_cmd}]
    })
    changed = changed or replaced
    ok('Updated UserPromptSubmit hook' if replaced else 'Set UserPromptSubmit hook')

    # Status line — chain to any existing command so we don't clobber the user's setup
    statusline_cmd = _hook_command('statusline.py')
    existing_sl = settings.get('statusLine', {})
    existing_sl_cmd = existing_sl.get('command', '') if isinstance(existing_sl, dict) else ''

    _is_ours = existing_sl_cmd and 'statusline.py' in existing_sl_cmd
    if existing_sl_cmd != statusline_cmd:
        # Only chain if the existing command is NOT a stale TTS statusline
        if existing_sl_cmd and not _is_ours:
            chain_file = os.path.join(INSTALL_DIR, 'statusline_chain.txt')
            with open(chain_file, 'w', encoding='utf-8') as f:
                f.write(existing_sl_cmd)
            ok(f'Saved existing statusLine command to statusline_chain.txt')

        settings['statusLine'] = {'type': 'command', 'command': statusline_cmd}
        changed = True
        ok('Updated statusLine' if _is_ours else 'Added statusLine for TTS status display')
    else:
        ok('statusLine already configured')

    if not changed:
        ok('settings already up to date')
        return

    # Backup before writing
    if os.path.exists(SETTINGS_FILE):
        backup = SETTINGS_FILE + '.bak'
        shutil.copy2(SETTINGS_FILE, backup)
        ok(f'Backed up original to settings.json.bak')

    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    ok(f'settings saved')


def print_success():
    on_file = os.path.join(INSTALL_DIR, 'on')
    scope_note = '(global)' if GLOBAL_SCOPE else '(project-local)'
    print(f"""
  DONE: claude-code-tts installed.

  Hooks:    {INSTALL_DIR}
  Skill:    {SKILL_INSTALL_DIR} {scope_note}
  Settings: {SETTINGS_FILE} {scope_note}

  Quick test:
    Run Claude Code and ask anything -- the response will be read aloud.

  /voice                          Toggle TTS on/off
  /voice stop                     Stop speech + disable TTS
  /voice repeat                   Replay last response
  /voice read <file|folder>       Read a file or folder aloud
  /voice change <name|description> Change the default voice
  /voice <name> [faster|slower]   Quick voice/speed shortcut

  Status line shows TTS state and voice at the bottom of Claude Code.

  Full docs: INSTALL.md
""")


def main():
    global INSTALL_DIR, MODELS_DIR, SKILL_INSTALL_DIR, SETTINGS_FILE, GLOBAL_SCOPE

    parser = argparse.ArgumentParser(description='claude-code-tts installer')
    parser.add_argument(
        '--dir', metavar='PATH',
        help='Override hook install directory (for testing only)'
    )
    parser.add_argument(
        '--global', dest='global_scope', action='store_true',
        help='Install skill and settings into ~/.claude/ (all projects) instead of ./.claude/ (current project)'
    )
    args = parser.parse_args()

    testing = bool(args.dir)
    if testing:
        INSTALL_DIR = os.path.abspath(args.dir)
        MODELS_DIR = os.path.join(INSTALL_DIR, 'models')

    if args.global_scope:
        GLOBAL_SCOPE = True
        INSTALL_DIR          = os.path.join(_home_claude, 'hooks', 'tts')
        MODELS_DIR           = os.path.join(INSTALL_DIR, 'models')
        SKILL_INSTALL_DIR = os.path.join(_home_claude, 'skills', 'voice')
        SETTINGS_FILE        = os.path.join(_home_claude, 'settings.json')

    scope_label = 'global (~/.claude/)' if args.global_scope else 'project-local (.claude/)'
    print(f'\nclaude-code-tts installer  [{scope_label}]\n')
    check_python()
    install_packages()
    create_dirs()
    copy_files()
    enable_tts()
    offer_kokoro()

    if testing:
        step(f'Test install mode (--dir): skipping settings.json patch and skill install.')
        ok(f'Hook files installed to {INSTALL_DIR}')
    else:
        copy_skill()
        patch_settings_json()

    print_success()


if __name__ == '__main__':
    main()
