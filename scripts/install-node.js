#!/usr/bin/env node
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const code = `import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())`;
const result = spawnSync('python', ['-c', code, '--', ...args], { stdio: 'inherit' });
if (result.error && result.error.code === 'ENOENT') {
  const fallback = spawnSync('python3', ['-c', code, '--', ...args], { stdio: 'inherit' });
  if (fallback.error) {
    console.error('Python is required. Please install Python 3.11+ and retry.');
    process.exit(1);
  }
  process.exit(fallback.status || 0);
}
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status || 0);
