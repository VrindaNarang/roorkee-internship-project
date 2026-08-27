import { useMemo, useState } from 'react'
import { Box, Chip, Pagination, Stack } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { DataTable } from '../components/table/DataTable'
import { StatusChip } from '../components/common/StatusChip'
import { PageIntro } from '../components/common/PageIntro'
import { SearchInput } from '../components/filters/SearchInput'
import { FilterBar } from '../components/filters/FilterBar'
import { useProductCategories, useProducts } from '../hooks/useProductQueries'
import { formatCurrency, formatNumber } from '../utils/format'
import type { ProductListItem } from '../api/types'

const PAGE_SIZE = 20

export default function Products() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)

  const categories = useProductCategories()

  const params = useMemo(
    () => ({
      search: search || undefined,
      category: category || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [search, category, page],
  )

  const products = useProducts(params)

  const handleCategoryClick = (name: string) => {
    setCategory((prev) => (prev === name ? '' : name))
    setPage(1)
  }

  return (
    <>
      <PageIntro description="Browse the product catalog, ranked by lifetime revenue." />

      <FilterBar>
        <Stack spacing={1.5} sx={{ width: '100%' }}>
          <Box sx={{ maxWidth: 320 }}>
            <SearchInput
              value={search}
              onChange={(v) => {
                setSearch(v)
                setPage(1)
              }}
              placeholder="Search by name or SKU…"
              fullWidth
            />
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip
              label="All categories"
              size="small"
              color={category === '' ? 'primary' : 'default'}
              variant={category === '' ? 'filled' : 'outlined'}
              onClick={() => handleCategoryClick('')}
            />
            {(categories.data ?? []).map((cat) => (
              <Chip
                key={cat.id}
                label={cat.name}
                size="small"
                color={category === cat.name ? 'primary' : 'default'}
                variant={category === cat.name ? 'filled' : 'outlined'}
                onClick={() => handleCategoryClick(cat.name)}
              />
            ))}
          </Stack>
        </Stack>
      </FilterBar>

      <DataTable<ProductListItem>
        columns={[
          { key: 'sku', label: 'SKU', render: (r) => r.sku },
          { key: 'name', label: 'Name', render: (r) => r.name },
          { key: 'category', label: 'Category', render: (r) => r.category },
          {
            key: 'unit_price',
            label: 'Unit Price',
            align: 'right',
            render: (r) => formatCurrency(r.unit_price),
          },
          {
            key: 'total_quantity_sold',
            label: 'Units Sold',
            align: 'right',
            render: (r) => formatNumber(r.total_quantity_sold),
          },
          {
            key: 'total_revenue',
            label: 'Revenue',
            align: 'right',
            render: (r) => formatCurrency(r.total_revenue),
          },
          {
            key: 'is_active',
            label: 'Status',
            render: (r) => <StatusChip value={r.is_active ? 'active' : 'inactive'} />,
          },
        ]}
        rows={products.data?.items ?? []}
        getRowKey={(r) => r.id}
        loading={products.isLoading}
        error={products.isError}
        onRetry={() => products.refetch()}
        onRowClick={(r) => navigate(`/products/${r.id}`)}
        emptyTitle="No products found"
        emptyDescription="Try a different search term or category."
        skeletonRows={8}
      />

      {products.data && products.data.meta.total_pages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2.5 }}>
          <Pagination
            count={products.data.meta.total_pages}
            page={page}
            onChange={(_, value) => setPage(value)}
            color="primary"
            shape="rounded"
          />
        </Box>
      )}
    </>
  )
}
