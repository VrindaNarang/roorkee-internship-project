import { useMemo, useState } from 'react'
import { Box, Pagination } from '@mui/material'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { DataTable } from '../components/table/DataTable'
import { StatusChip } from '../components/common/StatusChip'
import { PageIntro } from '../components/common/PageIntro'
import { SearchInput } from '../components/filters/SearchInput'
import { SelectFilter } from '../components/filters/SelectFilter'
import { FilterBar } from '../components/filters/FilterBar'
import { HealthScoreBar } from '../components/health/HealthScoreBar'
import { HealthTrendIndicator } from '../components/health/HealthTrendIndicator'
import { useCustomerHealthList, useCustomers, useCustomerStates } from '../hooks/useCustomerQueries'
import { formatCurrency, formatDate, formatNumber } from '../utils/format'
import type { CustomerHealthListItem, CustomerListItem } from '../api/types'

const INSTITUTION_TYPE_OPTIONS = [
  { value: 'government', label: 'Government' },
  { value: 'private', label: 'Private' },
  { value: 'university', label: 'University' },
  { value: 'research_lab', label: 'Research Lab' },
  { value: 'industry', label: 'Industry' },
]

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'dormant', label: 'Dormant' },
]

const PAGE_SIZE = 20

export default function Customers() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('search') ?? '')
  const [state, setState] = useState('')
  const [institutionType, setInstitutionType] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const states = useCustomerStates()

  const params = useMemo(
    () => ({
      search: search || undefined,
      state: state || undefined,
      institution_type: institutionType || undefined,
      status: status || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [search, state, institutionType, status, page],
  )

  const customers = useCustomers(params)
  const health = useCustomerHealthList()
  const healthByCollegeId = useMemo(() => {
    const map = new Map<number, CustomerHealthListItem>()
    for (const item of health.data ?? []) map.set(item.college_id, item)
    return map
  }, [health.data])

  const handleFilterChange = (setter: (value: string) => void) => (value: string) => {
    setter(value)
    setPage(1)
  }

  return (
    <>
      <PageIntro description="Browse and filter every institutional customer, ranked by lifetime revenue." />

      <FilterBar>
        <Box sx={{ minWidth: 240, flexGrow: { xs: 1, sm: 0 } }}>
          <SearchInput
            value={search}
            onChange={handleFilterChange(setSearch)}
            placeholder="Search by name or city…"
            fullWidth
          />
        </Box>
        <SelectFilter
          label="State"
          value={state}
          onChange={handleFilterChange(setState)}
          options={(states.data ?? []).map((s) => ({ value: s, label: s }))}
        />
        <SelectFilter
          label="Institution Type"
          value={institutionType}
          onChange={handleFilterChange(setInstitutionType)}
          options={INSTITUTION_TYPE_OPTIONS}
        />
        <SelectFilter
          label="Status"
          value={status}
          onChange={handleFilterChange(setStatus)}
          options={STATUS_OPTIONS}
        />
      </FilterBar>

      <DataTable<CustomerListItem>
        columns={[
          { key: 'name', label: 'Name', render: (r) => r.name },
          {
            key: 'institution_type',
            label: 'Type',
            render: (r) => <StatusChip value={r.institution_type} />,
          },
          { key: 'state', label: 'State', render: (r) => r.state },
          { key: 'region', label: 'Region', render: (r) => r.region },
          { key: 'status', label: 'Status', render: (r) => <StatusChip value={r.status} /> },
          {
            key: 'total_orders',
            label: 'Orders',
            align: 'right',
            render: (r) => formatNumber(r.total_orders),
          },
          {
            key: 'total_revenue',
            label: 'Revenue',
            align: 'right',
            render: (r) => formatCurrency(r.total_revenue),
          },
          { key: 'last_order_date', label: 'Last Order', render: (r) => formatDate(r.last_order_date) },
          {
            key: 'health_score',
            label: 'Health Score',
            render: (r) => {
              const h = healthByCollegeId.get(r.id)
              return h ? <HealthScoreBar score={h.health_score} status={h.health_status} /> : '—'
            },
          },
          {
            key: 'health_status',
            label: 'Risk',
            render: (r) => {
              const h = healthByCollegeId.get(r.id)
              return h ? <StatusChip value={h.health_status} /> : '—'
            },
          },
          {
            key: 'health_trend',
            label: 'Trend',
            render: (r) => {
              const h = healthByCollegeId.get(r.id)
              return h ? (
                <HealthTrendIndicator
                  trend={h.health_trend}
                  currentScore={h.health_score}
                  previousScore={h.previous_health_score}
                />
              ) : (
                '—'
              )
            },
          },
        ]}
        rows={customers.data?.items ?? []}
        getRowKey={(r) => r.id}
        loading={customers.isLoading}
        error={customers.isError}
        onRetry={() => customers.refetch()}
        onRowClick={(r) => navigate(`/customers/${r.id}`)}
        emptyTitle="No customers found"
        emptyDescription="Try adjusting your search or filters."
        skeletonRows={8}
      />

      {customers.data && customers.data.meta.total_pages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2.5 }}>
          <Pagination
            count={customers.data.meta.total_pages}
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
