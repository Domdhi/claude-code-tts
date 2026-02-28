#!/usr/bin/env node
'use strict'

const { execFileSync } = require('child_process')
const path = require('path')

// Find Python — try python3 first on Mac/Linux, python first on Windows
const candidates = process.platform === 'win32'
  ? ['python', 'python3']
  : ['python3', 'python']

let python = null
for (const candidate of candidates) {
  try {
    execFileSync(candidate, ['--version'], { stdio: 'ignore' })
    python = candidate
    break
  } catch {
    // not found, try next
  }
}

if (!python) {
  console.error('Error: Python 3.10+ is required but was not found.')
  console.error('Install Python from https://python.org and try again.')
  process.exit(1)
}

const script = path.join(__dirname, '..', 'install.py')
const args = process.argv.slice(2)  // pass through --dir and any other flags

try {
  execFileSync(python, [script, ...args], { stdio: 'inherit' })
} catch (e) {
  process.exit(e.status ?? 1)
}
