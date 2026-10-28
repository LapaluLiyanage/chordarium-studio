# Chordarium brand — extracted

Source repo: https://github.com/LapaluLiyanage/Chordarium (read-only; cloned 2026-10-28). Nothing was invented.

| Item | Value | Source |
| --- | --- | --- |
| Logo | "C" ring + 3 beat dots; top dot amber, others follow `currentColor`; viewBox 100×100 | client/src/components/Logo.tsx |
| App icon | Ink circle `#231d17`, cream ring, amber top dot | client/index.html (favicon data-URI) |
| Primary accent | Amber `#f2913d` | styles.css :root |
| Secondary accent | Blue `#6aa8e0` (focus ring) | styles.css |
| Light surfaces | cream `#fbf5ea`, sand `#efe5d4`, paper `#fffdf8`, ink `#231d17` | styles.css |
| Dark surfaces | `#1f1a16`, `#2a241e`, line `#3d352d`, text `#f6eee1`, muted `#b9ad9c`; chord chip `#342c25` | styles.css |
| Accents | purple `#b48be0`, green `#6fbf8b`, coral `#ee8577`, yellow `#f2c14e`, bass teal `#4fc3c9`, danger `#c2410c` | styles.css |
| Section colours | intro yellow, verse blue, chorus amber, bridge purple, interlude coral, outro green, other `#b9ad9c` | client/src/sections.ts |
| Font | Archivo variable (wght 100–900, wdth 62–125), bundled woff2 (latin, latin-ext, vietnamese) + TTFs for PDF. Signature = weight 900, width 62%, uppercase for wordmark | styles.css |
| Shape | pills (999px), cards 22–32px, chips 10px, bar cells 14px, 2px ink outlines in light mode | styles.css |
| Motion engine | GSAP 3 + ScrollTrigger, Lenis smooth scroll | client/package.json, Effects.tsx |
| Signature motion | chord flip-in (0.5s back.out(2)); wordmark letter rise (stagger .055, power4.out); logo spin-in; CTA pulse ring; magnetic buttons; floating note bursts; custom cursor ring | motion.ts, Hero.tsx, Effects.tsx |
| Reduced motion | all animation disabled under `prefers-reduced-motion` | styles.css |

Derived (Studio-only, needs Lapalu's approval): `--role-drums` = coral (Chordarium has no drum colour); piano amber, bass teal (`--bass`), pad purple.
Contrast to verify at build time: amber/coral/teal/purple on `#2a241e` ≥ 3:1.
Not present in Chordarium: Sinhala font (use Noto Sans Sinhala), a gradient (none used), a mono font (chords use Archivo condensed 900).
