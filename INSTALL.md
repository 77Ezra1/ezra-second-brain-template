# Install by Sending This Link to Your Agent

Copy this repository URL and send it to any shell-capable AI agent:

```text
https://github.com/77Ezra1/ezra-second-brain-template
```

Suggested message:

```text
Please install this local-first second brain for me:
https://github.com/77Ezra1/ezra-second-brain-template

Use the installer for my operating system, do not overwrite existing private data, run validation, and tell me the install path plus the first capture/query commands.
```

The repository includes `AGENTS.md`, so compatible agents can infer the install steps directly from the repo.

## Direct install commands

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-windows.ps1 | iex
```

### Universal Python fallback

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

## What gets installed

By default the workspace is created at:

- macOS/Linux: `~/second-brain`
- Windows: `%USERPROFILE%\second-brain`

Private records live under `data/` in that workspace. The public template does not include private records.
