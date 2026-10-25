export function fmtMAD(n: number, opts: { compact?: boolean } = {}): string {
  if (opts.compact) {
    if (n >= 1e9) return (n / 1e9).toFixed(2).replace(/\.?0+$/, '') + ' Md'
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + ' M'
    if (n >= 1e3) return (n / 1e3).toFixed(0) + ' k'
    return String(n)
  }
  return new Intl.NumberFormat('fr-FR').format(Math.round(n))
}

export function fmtInt(n: number): string {
  return new Intl.NumberFormat('fr-FR').format(n)
}
