import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DataTable } from './DataTable'

interface Row {
  id: number
  name: string
}

const columns = [{ key: 'name', label: 'Name', render: (r: Row) => r.name }]
const rows: Row[] = [
  { id: 1, name: 'Alpha College' },
  { id: 2, name: 'Beta College' },
]

describe('DataTable', () => {
  it('renders every row using the column render function', () => {
    render(<DataTable columns={columns} rows={rows} getRowKey={(r) => r.id} />)
    expect(screen.getByText('Alpha College')).toBeInTheDocument()
    expect(screen.getByText('Beta College')).toBeInTheDocument()
  })

  it('shows skeleton placeholders instead of rows while loading', () => {
    render(<DataTable columns={columns} rows={[]} getRowKey={(r: Row) => r.id} loading skeletonRows={3} />)
    expect(screen.queryByText('Alpha College')).not.toBeInTheDocument()
    expect(document.querySelectorAll('.MuiSkeleton-root').length).toBeGreaterThan(0)
  })

  it('shows an empty state with no rows, no loading, no error', () => {
    render(
      <DataTable
        columns={columns}
        rows={[]}
        getRowKey={(r: Row) => r.id}
        emptyTitle="Nothing here"
        emptyDescription="Try a different filter"
      />,
    )
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
  })

  it('shows an error state with a retry action when the fetch failed', async () => {
    const onRetry = vi.fn()
    render(<DataTable columns={columns} rows={[]} getRowKey={(r: Row) => r.id} error onRetry={onRetry} />)
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('calls onRowClick with the clicked row', async () => {
    const onRowClick = vi.fn()
    render(<DataTable columns={columns} rows={rows} getRowKey={(r) => r.id} onRowClick={onRowClick} />)
    await userEvent.click(screen.getByText('Alpha College'))
    expect(onRowClick).toHaveBeenCalledWith(rows[0])
  })
})
