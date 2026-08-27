const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const compactCurrencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
})

const numberFormatter = new Intl.NumberFormat('en-IN')

export const formatCurrency = (value: number) => currencyFormatter.format(value)

export const formatCompactCurrency = (value: number) => compactCurrencyFormatter.format(value)

export const formatNumber = (value: number) => numberFormatter.format(value)

export const formatPct = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(1)}%`

export const formatDate = (value: string | null | undefined) => {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export const formatMonth = (value: string) => {
  const [year, month] = value.split('-')
  const date = new Date(Number(year), Number(month) - 1, 1)
  return date.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' })
}
