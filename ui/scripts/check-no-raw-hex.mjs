// Brand rule: components use CSS tokens only. Raw hex colours are allowed only in src/brand/.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
const bad = []
const walk = (d) => { for (const f of readdirSync(d)) { const p = join(d, f); if (p.includes(join('src', 'brand'))) continue
  if (statSync(p).isDirectory()) walk(p); else if (/\.(tsx?|css)$/.test(f) && !/\.test\./.test(f)) {
    readFileSync(p, 'utf8').split('\n').forEach((l, i) => { if (/#[0-9a-fA-F]{3,8}\b/.test(l.replace(/'#888'/, ''))) bad.push(`${p}:${i + 1}: ${l.trim()}`) }) } } }
walk('src')
if (bad.length) { console.error('Raw hex colours found:\n' + bad.join('\n')); process.exit(1) }
console.log('no raw hex colours')
