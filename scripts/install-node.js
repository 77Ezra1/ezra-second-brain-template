#!/usr/bin/env node
const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
const localInstaller = path.join(__dirname, 'install.py');

function runPython(commandArgs) {
  let result = spawnSync('python', commandArgs, { stdio: 'inherit' });
  if (result.error && result.error.code === 'ENOENT') {
    result = spawnSync('python3', commandArgs, { stdio: 'inherit' });
  }
  if (result.error) {
    console.error('Python is required. Please install Python 3.11+ and retry.');
    process.exit(1);
  }
  process.exit(result.status || 0);
}

// When this package is installed by npx from GitHub, install.py is available next to this file.
// Running the local file also makes --skip-download work for smoke tests and offline agents.
if (fs.existsSync(localInstaller)) {
  runPython([localInstaller, ...args]);
}

// Fallback for unusual packaging environments where only this wrapper exists.
const code = `import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())`;
runPython(['-c', code, '--', ...args]);
