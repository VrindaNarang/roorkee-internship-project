import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusChip } from './StatusChip'

describe('StatusChip', () => {
  it('renders the value as a capitalized, underscore-free label', () => {
    render(<StatusChip value="at_risk" />)
    expect(screen.getByText('at risk')).toBeInTheDocument()
  })

  it('applies the success color for a healthy/active-style status', () => {
    render(<StatusChip value="healthy" />)
    const chip = screen.getByText('healthy').closest('.MuiChip-root')
    expect(chip).toHaveClass('MuiChip-colorSuccess')
  })

  it('applies the error color for a critical/high-priority status', () => {
    render(<StatusChip value="critical" />)
    const chip = screen.getByText('critical').closest('.MuiChip-root')
    expect(chip).toHaveClass('MuiChip-colorError')
  })

  it('falls back to an outlined default chip for an unrecognized value', () => {
    render(<StatusChip value="some_unknown_status" />)
    const chip = screen.getByText('some unknown status').closest('.MuiChip-root')
    expect(chip).toHaveClass('MuiChip-outlinedDefault')
  })
})
