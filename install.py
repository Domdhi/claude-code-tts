#!/usr/bin/env python3
"""
claude-code-tts installer
Copies hook files to ~/.claude/hooks/tts/, installs slash commands, and patches settings.json.
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
HOOK_FILES = ['daemon.py', 'stop.py', 'task-hook.py', 'repeat.py']
COMMAND_FILES = ['stop.md', 'repeat.md', 'on.md', 'off.md']

SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
HOOKS_SOURCE    = os.path.join(SOURCE_DIR, '.claude', 'hooks', 'tts')
COMMANDS_SOURCE = os.path.join(SOURCE_DIR, '.claude', 'commands', 'voice')

_home_claude = os.path.join(os.path.expanduser('~'), '.claude')
_proj_claude = os.path.join(os.getcwd(), '.claude')

# Default: project-local — all files go into ./.claude/ (current project)
# --global overrides all of these to ~/.claude/
INSTALL_DIR          = os.path.join(_proj_claude, 'hooks', 'tts')
MODELS_DIR           = os.path.join(INSTALL_DIR, 'models')
COMMANDS_INSTALL_DIR = os.path.join(_proj_claude, 'commands', 'voice')
# settings.local.json is gitignored — safe for machine-specific absolute paths
SETTINGS_FILE        = os.path.join(_proj_claude, 'settings.local.json')

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


def copy_commands():
    step('Installing slash command files...')
    os.makedirs(COMMANDS_INSTALL_DIR, exist_ok=True)
    for filename in COMMAND_FILES:
        src = os.path.join(COMMANDS_SOURCE, filename)
        dst = os.path.join(COMMANDS_INSTALL_DIR, filename)
        if not os.path.exists(src):
            warn(f'Command file not found: {src} -- skipping')
            continue
        shutil.copy2(src, dst)
        ok(filename)


def enable_tts():
    step('Enabling TTS (creating on file)...')
    on_file = os.path.join(INSTALL_DIR, 'on')
    open(on_file, 'w').close()
    ok('TTS enabled')


def _kokoro_already_installed():
    """True if kokoro-onnx is importable and model files exist (in MODELS_DIR or default location)."""
    import importlib.util
    if importlib.util.find_spec('kokoro_onnx') is None:
        return False
    default_models = os.path.join(os.path.expanduser('~'), '.claude', 'hooks', 'tts', 'models')
    for models_dir in (MODELS_DIR, default_models):
        if all(os.path.exists(os.path.join(models_dir, f))
               for f in ('kokoro-v1.0.onnx', 'voices-v1.0.bin')):
            return True
    return False


def offer_kokoro():
    step('Offline fallback (kokoro-onnx, ~82MB download)')

    if _kokoro_already_installed():
        ok('kokoro-onnx already installed, skipping')
        return

    print('    Edge TTS requires internet. kokoro-onnx is a local fallback that works offline.')
    resp = input('    Install kokoro-onnx offline fallback? [y/N] ').strip().lower()
    if resp != 'y':
        ok('Skipped (edge-tts only mode)')
        return

    step('Installing kokoro-onnx...')
    pip_install(KOKORO_PACKAGES)
    ok('kokoro-onnx installed')

    step('Downloading model files...')
    os.makedirs(MODELS_DIR, exist_ok=True)
    try:
        import urllib.request
        for url, filename in KOKORO_MODEL_URLS:
            dst = os.path.join(MODELS_DIR, filename)
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


def _has_command(hook_list, command):
    """Return True if command already appears in any entry in hook_list."""
    for entry in hook_list:
        for h in entry.get('hooks', []):
            if h.get('command') == command:
                return True
    return False


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
    if not _has_command(hooks.get('Stop', []), stop_cmd):
        hooks.setdefault('Stop', []).append({
            'hooks': [{'type': 'command', 'command': stop_cmd}]
        })
        changed = True
        ok('Added Stop hook')
    else:
        ok('Stop hook already registered')

    # PostToolUse:Task hook
    if not _has_command(hooks.get('PostToolUse', []), task_cmd):
        hooks.setdefault('PostToolUse', []).append({
            'matcher': 'Task',
            'hooks': [{'type': 'command', 'command': task_cmd}]
        })
        changed = True
        ok('Added PostToolUse:Task hook')
    else:
        ok('PostToolUse:Task hook already registered')

    # UserPromptSubmit hook
    if not _has_command(hooks.get('UserPromptSubmit', []), repeat_cmd):
        hooks.setdefault('UserPromptSubmit', []).append({
            'hooks': [{'type': 'command', 'command': repeat_cmd}]
        })
        changed = True
        ok('Added UserPromptSubmit hook')
    else:
        ok('UserPromptSubmit hook already registered')

    if not changed:
        ok('settings.json already up to date')
        return

    # Backup before writing
    if os.path.exists(SETTINGS_FILE):
        backup = SETTINGS_FILE + '.bak'
        shutil.copy2(SETTINGS_FILE, backup)
        ok(f'Backed up original to settings.json.bak')

    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
    ok(f'settings.json saved')


def print_success():
    on_file = os.path.join(INSTALL_DIR, 'on')
    scope_note = '(global)' if GLOBAL_SCOPE else '(project-local)'
    print(f"""
  DONE: claude-code-tts installed.

  Hooks:     {INSTALL_DIR}
  Commands:  {COMMANDS_INSTALL_DIR} {scope_note}
  Settings:  {SETTINGS_FILE} {scope_note}

  Quick test:
    Run Claude Code and ask anything -- the response will be read aloud.

  Commands (type in Claude Code prompt):
    /voice:stop    Stop speech immediately
    /voice:repeat  Replay last response
    /voice:on      Re-enable TTS
    /voice:off     Disable TTS

  To disable TTS:
    Delete {on_file}

  Full docs: INSTALL.md
""")


def main():
    global INSTALL_DIR, MODELS_DIR, COMMANDS_INSTALL_DIR, SETTINGS_FILE, GLOBAL_SCOPE

    parser = argparse.ArgumentParser(description='claude-code-tts installer')
    parser.add_argument(
        '--dir', metavar='PATH',
        help='Override hook install directory (for testing only)'
    )
    parser.add_argument(
        '--global', dest='global_scope', action='store_true',
        help='Install commands and settings into ~/.claude/ (all projects) instead of ./.claude/ (current project)'
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
        COMMANDS_INSTALL_DIR = os.path.join(_home_claude, 'commands', 'voice')
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
        step(f'Test install mode (--dir): skipping settings.json patch and command install.')
        ok(f'Hook files installed to {INSTALL_DIR}')
    else:
        copy_commands()
        patch_settings_json()

    print_success()


if __name__ == '__main__':
    main()
