#!/usr/bin/env node

const allowed = new Set(["build", "lint", "typecheck", "test"]);
const command = process.argv[2];

if (!allowed.has(command)) {
  console.error(`Unsupported placeholder command: ${command || "(missing)"}`);
  process.exit(1);
}

console.log(`zayd-platform ${command}: workspace placeholder`);
