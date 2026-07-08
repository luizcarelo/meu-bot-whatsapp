const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');

const root = path.resolve(__dirname, '..');
const files = [];

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === 'dist') {
        continue;
      }
      walk(full);
      continue;
    }
    if (entry.isFile() && entry.name.endsWith('.js')) {
      files.push(full);
    }
  }
}

walk(path.join(root, 'src'));

for (const file of files) {
  childProcess.execFileSync('node', ['--check', file], { stdio: 'inherit' });
}

console.log('Syntax check OK:', files.length);
