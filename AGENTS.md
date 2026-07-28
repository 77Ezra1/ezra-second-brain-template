# Agent Install Instructions

If a user sends you this repository URL and asks to install or set up an 外脑 / second brain, treat the URL itself as an install request.

Repository:

```text
https://github.com/77Ezra1/ezra-second-brain-template
```

## Default goal

Install a local-first second-brain workspace for the current user without overwriting existing private data.

## Choose the platform automatically

- macOS / Linux shell: use the macOS shell installer on macOS, or the Python installer with `--platform linux` on Linux.
- Windows PowerShell: use the Windows PowerShell installer.
- If uncertain, clone the repo and run `python scripts/install.py --platform auto`.

## One-command install

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-windows.ps1 | iex
```

### Cross-platform Python fallback

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

On Windows, prefer:

```powershell
py -3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --platform windows
```

## Install behavior

The installer:

1. Creates a local workspace, defaulting to `~/second-brain` or `%USERPROFILE%\second-brain`.
2. Copies reusable template files.
3. Creates private runtime directories under `data/`.
4. Writes `config/brain.yaml` from `config/brain.example.yaml` with the local data path and detected platform.
5. Runs validation when possible.
6. Prints example capture/query commands.

## Safety rules

- Do not upload or publish the user's installed `data/` directory.
- Do not commit `.env`, credentials, cookies, tokens, raw captures, inbox files, generated wiki notes, daily reports, or reviews.
- If the target directory already exists and is not empty, do not overwrite it unless the user explicitly approves `--force`.
- If Python is missing, tell the user to install Python 3.11+ and rerun the command.

## Post-install verification

Run a smoke test in the installed workspace:

```bash
python scripts/brain_cli.py validate
python scripts/telegram_brain_router.py --text "外脑：今天安装了本地外脑" --source cli --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source cli --data-dir ./data
```

Use `py -3` instead of `python` on Windows when needed.
