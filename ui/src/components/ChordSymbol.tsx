import { splitChord } from '../chords'

export function ChordSymbol({ symbol }: { symbol: string }) {
  const p = splitChord(symbol)
  return (
    <span className="cs" aria-label={symbol}>
      {p.root}<small>{p.quality}</small>{p.ext && <sup>{p.ext}</sup>}{p.bass && <span className="bass">/{p.bass}</span>}
    </span>
  )
}
