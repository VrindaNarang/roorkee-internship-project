import {
  Paper,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import type { ReactNode } from 'react'
import { EmptyState } from '../common/EmptyState'
import { ErrorState } from '../common/ErrorState'

export interface DataTableColumn<T> {
  key: string
  label: string
  align?: 'left' | 'right' | 'center'
  width?: string | number
  render: (row: T) => ReactNode
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => string | number
  loading?: boolean
  error?: boolean
  errorMessage?: string
  onRetry?: () => void
  emptyTitle?: string
  emptyDescription?: string
  onRowClick?: (row: T) => void
  skeletonRows?: number
  dense?: boolean
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  loading,
  error,
  errorMessage,
  onRetry,
  emptyTitle,
  emptyDescription,
  onRowClick,
  skeletonRows = 5,
  dense,
}: DataTableProps<T>) {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size={dense ? 'small' : 'medium'}>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell key={col.key} align={col.align ?? 'left'} width={col.width}>
                {col.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading &&
            Array.from({ length: skeletonRows }).map((_, rowIdx) => (
              <TableRow key={rowIdx}>
                {columns.map((col) => (
                  <TableCell key={col.key} align={col.align ?? 'left'}>
                    <Skeleton variant="text" />
                  </TableCell>
                ))}
              </TableRow>
            ))}

          {!loading && error && (
            <TableRow>
              <TableCell colSpan={columns.length} sx={{ border: 0 }}>
                <ErrorState message={errorMessage} onRetry={onRetry} />
              </TableCell>
            </TableRow>
          )}

          {!loading && !error && rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={columns.length} sx={{ border: 0 }}>
                <EmptyState title={emptyTitle} description={emptyDescription} />
              </TableCell>
            </TableRow>
          )}

          {!loading &&
            !error &&
            rows.map((row) => (
              <TableRow
                key={getRowKey(row)}
                hover
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                sx={onRowClick ? { cursor: 'pointer' } : undefined}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} align={col.align ?? 'left'}>
                    {col.render(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}
