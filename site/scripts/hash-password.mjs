#!/usr/bin/env node
// Prompts for a password and prints its SHA-256 hash — paste the result
// into src/data/lock.ts. Run: npm run hash-password
import { createInterface } from 'node:readline/promises';
import { createHash } from 'node:crypto';

const rl = createInterface({ input: process.stdin, output: process.stdout });
const password = await rl.question('New shared password: ');
rl.close();

const hash = createHash('sha256').update(password.trim()).digest('hex');
console.log('\nHash (paste into site/src/data/lock.ts as LOCK_HASH):\n');
console.log(hash);
