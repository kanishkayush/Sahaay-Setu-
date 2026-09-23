/**
 * Indian-format money and number helpers.
 * Amounts use the lakh/crore grouping (₹1,40,000, not ₹140,000) because that is
 * how our users read numbers.
 */

export function formatCurrency(amount: number, withSymbol = true): string {
  if (amount == null || Number.isNaN(amount)) return '—';
  const formatted = Math.round(amount).toLocaleString('en-IN');
  return withSymbol ? `₹${formatted}` : formatted;
}

/** Compact Indian form: ₹1.4 लाख / ₹50 lakh / ₹1.2 crore. */
export function formatCompactCurrency(amount: number): string {
  if (amount == null || Number.isNaN(amount)) return '—';
  if (amount >= 10_000_000) {
    const cr = amount / 10_000_000;
    return `₹${cr % 1 === 0 ? cr : cr.toFixed(2)} crore`;
  }
  if (amount >= 100_000) {
    const lakh = amount / 100_000;
    return `₹${lakh % 1 === 0 ? lakh : lakh.toFixed(2)} lakh`;
  }
  if (amount >= 1_000) {
    return `₹${(amount / 1_000).toFixed(amount % 1000 === 0 ? 0 : 1)}k`;
  }
  return `₹${Math.round(amount)}`;
}

export function formatPercent(value: number): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value % 1 === 0 ? value : value.toFixed(2).replace(/0$/, '')}%`;
}

export function formatMonths(months: number, monthWord: string, yearWord: string): string {
  if (months == null || Number.isNaN(months)) return '—';
  if (months < 12) return `${months} ${monthWord}`;
  const years = Math.floor(months / 12);
  const rest = months % 12;
  return rest === 0 ? `${years} ${yearWord}` : `${years} ${yearWord} ${rest} ${monthWord}`;
}

/** Parses "1,40,000" / "₹1.4L" style user input into a number. */
export function parseAmountInput(input: string): number {
  if (!input) return 0;
  const cleaned = input.replace(/[^0-9.]/g, '');
  const value = Number.parseFloat(cleaned);
  return Number.isFinite(value) ? Math.round(value) : 0;
}

/**
 * Ultra-compact money, for stat rows where three values share one line.
 * "₹50L" not "₹50 lakh" — the long form wraps and breaks the row, and it wraps
 * worse in Indic scripts where the surrounding labels are longer.
 * Use formatCompactCurrency in prose, this only in tight columns.
 */
export function formatStatCurrency(amount: number): string {
  if (amount == null || Number.isNaN(amount)) return '—';
  // Two decimals, trailing zeros trimmed: ₹1.26L, ₹2.77L, ₹50L. One decimal
  // would round ₹1,26,000 to "₹1.3L" and ₹2,76,624 to "₹2.8L", losing thousands
  // of rupees of precision on the figure a user is comparing schemes by.
  const trim = (n: number) => n.toFixed(2).replace(/\.?0+$/, '');
  if (amount >= 10_000_000) return `₹${trim(amount / 10_000_000)}Cr`;
  if (amount >= 100_000) return `₹${trim(amount / 100_000)}L`;
  if (amount >= 1_000) return `₹${Math.round(amount / 1_000)}k`;
  return `₹${Math.round(amount)}`;
}
