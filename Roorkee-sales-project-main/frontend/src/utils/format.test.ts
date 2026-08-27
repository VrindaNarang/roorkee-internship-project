import { describe, expect, it } from 'vitest'
import { formatCompactCurrency, formatCurrency, formatDate, formatMonth, formatNumber, formatPct } from './format'

describe('formatCurrency', () => {
  it('formats a rupee amount with the ₹ symbol and no decimals', () => {
    expect(formatCurrency(150000)).toBe('₹1,50,000')
  })

  it('formats zero correctly', () => {
    expect(formatCurrency(0)).toBe('₹0')
  })
})

describe('formatCompactCurrency', () => {
  it('formats a large amount in Lakh/Crore notation', () => {
    expect(formatCompactCurrency(1_200_000)).toContain('L')
  })
})

describe('formatNumber', () => {
  it('formats with Indian digit grouping', () => {
    expect(formatNumber(1234567)).toBe('12,34,567')
  })
})

describe('formatPct', () => {
  it('prefixes positive values with a plus sign', () => {
    expect(formatPct(12.345)).toBe('+12.3%')
  })

  it('does not prefix negative values with an extra sign', () => {
    expect(formatPct(-8.2)).toBe('-8.2%')
  })

  it('does not prefix zero', () => {
    expect(formatPct(0)).toBe('0.0%')
  })
})

describe('formatDate', () => {
  it('formats an ISO date string as DD Mon YYYY', () => {
    expect(formatDate('2026-07-12T10:00:00Z')).toMatch(/12 Jul 2026/)
  })

  it('returns an em dash placeholder for null/undefined', () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate(undefined)).toBe('—')
  })
})

describe('formatMonth', () => {
  it('formats a YYYY-MM string as short month + 2-digit year', () => {
    expect(formatMonth('2026-03')).toMatch(/Mar 26/)
  })
})
