import { Box, Button, Typography } from '@mui/material'
import PaidOutlinedIcon from '@mui/icons-material/PaidOutlined'
import CalendarMonthOutlinedIcon from '@mui/icons-material/CalendarMonthOutlined'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import PeopleAltOutlinedIcon from '@mui/icons-material/PeopleAltOutlined'
import ShoppingCartOutlinedIcon from '@mui/icons-material/ShoppingCartOutlined'
import TrendingUpOutlinedIcon from '@mui/icons-material/TrendingUpOutlined'
import { useNavigate } from 'react-router-dom'
import { PageIntro } from '../components/common/PageIntro'
import { KpiCard } from '../components/dashboard/KpiCard'
import { ChartCard } from '../components/charts/ChartCard'
import { SalesTrendChart } from '../components/charts/SalesTrendChart'
import { RevenueByStateChart } from '../components/charts/RevenueByStateChart'
import { CategoryPieChart } from '../components/charts/CategoryPieChart'
import { HealthDistributionChart } from '../components/charts/HealthDistributionChart'
import { DataTable } from '../components/table/DataTable'
import { StatusChip } from '../components/common/StatusChip'
import { HealthScoreBar } from '../components/health/HealthScoreBar'
import { ProbabilityBar } from '../components/predictions/ProbabilityBar'
import {
  useCategoryDistribution,
  useDashboardSummary,
  useRecentOrders,
  useRevenueByState,
  useSalesTrend,
  useTopCustomers,
  useTopProducts,
} from '../hooks/useDashboardQueries'
import { useCriticalCustomers, useCustomerHealthList, useHealthyCustomers } from '../hooks/useCustomerQueries'
import { useTopOpportunities } from '../hooks/usePredictionQueries'
import { formatCurrency, formatDate, formatNumber } from '../utils/format'
import type { CustomerHealthListItem, CustomerPrediction, RecentOrder, TopCustomer, TopProduct } from '../api/types'

export default function Dashboard() {
  const navigate = useNavigate()
  const summary = useDashboardSummary()
  const salesTrend = useSalesTrend(12)
  const revenueByState = useRevenueByState()
  const categoryDistribution = useCategoryDistribution()
  const topCustomers = useTopCustomers(10)
  const topProducts = useTopProducts(10)
  const recentOrders = useRecentOrders(10)
  const healthList = useCustomerHealthList()
  const healthyCustomers = useHealthyCustomers(10)
  const criticalCustomers = useCriticalCustomers(10)
  const topOpportunities = useTopOpportunities(5)

  const s = summary.data

  return (
    <>
      <PageIntro description="Live sales performance across all customers, products, and regions." />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' },
          gap: 2.5,
          mb: 4,
        }}
      >
        <KpiCard
          label="Total Revenue"
          value={s ? formatCurrency(s.total_revenue) : undefined}
          icon={<PaidOutlinedIcon fontSize="small" />}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Monthly Revenue"
          value={s ? formatCurrency(s.monthly_revenue) : undefined}
          icon={<CalendarMonthOutlinedIcon fontSize="small" />}
          trendPct={s?.revenue_growth_pct}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Total Orders"
          value={s ? formatNumber(s.total_orders) : undefined}
          icon={<ReceiptLongOutlinedIcon fontSize="small" />}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Active Customers"
          value={s ? formatNumber(s.active_customers) : undefined}
          icon={<PeopleAltOutlinedIcon fontSize="small" />}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Average Order Value"
          value={s ? formatCurrency(s.average_order_value) : undefined}
          icon={<ShoppingCartOutlinedIcon fontSize="small" />}
          loading={summary.isLoading}
        />
        <KpiCard
          label="Revenue Growth"
          value={s ? `${s.revenue_growth_pct >= 0 ? '+' : ''}${s.revenue_growth_pct.toFixed(1)}%` : undefined}
          icon={<TrendingUpOutlinedIcon fontSize="small" />}
          loading={summary.isLoading}
        />
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' },
          gap: 2,
          mb: 2,
        }}
      >
        <ChartCard
          title="Monthly Sales Trend"
          subtitle="Revenue over the last 12 months"
          loading={salesTrend.isLoading}
          error={salesTrend.isError}
          onRetry={() => salesTrend.refetch()}
          isEmpty={(salesTrend.data ?? []).length === 0}
        >
          <SalesTrendChart data={salesTrend.data ?? []} />
        </ChartCard>

        <ChartCard
          title="Category Distribution"
          subtitle="Revenue share by product category"
          loading={categoryDistribution.isLoading}
          error={categoryDistribution.isError}
          onRetry={() => categoryDistribution.refetch()}
          isEmpty={(categoryDistribution.data ?? []).length === 0}
        >
          <CategoryPieChart data={categoryDistribution.data ?? []} />
        </ChartCard>
      </Box>

      <Box sx={{ mb: 2 }}>
        <ChartCard
          title="Revenue by State"
          subtitle="Top 8 states by total revenue"
          loading={revenueByState.isLoading}
          error={revenueByState.isError}
          onRetry={() => revenueByState.refetch()}
          isEmpty={(revenueByState.data ?? []).length === 0}
        >
          <RevenueByStateChart data={revenueByState.data ?? []} />
        </ChartCard>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' },
          gap: 2,
          mb: 2,
        }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
            Top 10 Customers
          </Typography>
          <DataTable<TopCustomer>
            columns={[
              { key: 'name', label: 'Customer', render: (r) => r.name },
              {
                key: 'institution_type',
                label: 'Type',
                render: (r) => <StatusChip value={r.institution_type} />,
              },
              { key: 'state', label: 'State', render: (r) => r.state },
              {
                key: 'total_revenue',
                label: 'Revenue',
                align: 'right',
                render: (r) => formatCurrency(r.total_revenue),
              },
              { key: 'total_orders', label: 'Orders', align: 'right', render: (r) => r.total_orders },
            ]}
            rows={topCustomers.data ?? []}
            getRowKey={(r) => r.id}
            loading={topCustomers.isLoading}
            error={topCustomers.isError}
            onRetry={() => topCustomers.refetch()}
            onRowClick={(r) => navigate(`/customers/${r.id}`)}
            emptyDescription="No customer revenue recorded yet."
            dense
          />
        </Box>

        <Box>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
            Top Selling Products
          </Typography>
          <DataTable<TopProduct>
            columns={[
              { key: 'name', label: 'Product', render: (r) => r.name },
              { key: 'category', label: 'Category', render: (r) => r.category },
              {
                key: 'total_revenue',
                label: 'Revenue',
                align: 'right',
                render: (r) => formatCurrency(r.total_revenue),
              },
              {
                key: 'total_quantity',
                label: 'Units',
                align: 'right',
                render: (r) => formatNumber(r.total_quantity),
              },
            ]}
            rows={topProducts.data ?? []}
            getRowKey={(r) => r.id}
            loading={topProducts.isLoading}
            error={topProducts.isError}
            onRetry={() => topProducts.refetch()}
            onRowClick={(r) => navigate(`/products/${r.id}`)}
            emptyDescription="No product sales recorded yet."
            dense
          />
        </Box>
      </Box>

      <Typography variant="h6" fontWeight={600} sx={{ mb: 1.5 }}>
        Customer Health
      </Typography>
      <Box sx={{ mb: 2 }}>
        <ChartCard
          title="Health Score Distribution"
          subtitle="Number of customers per 10-point score band"
          loading={healthList.isLoading}
          error={healthList.isError}
          onRetry={() => healthList.refetch()}
          isEmpty={(healthList.data ?? []).length === 0}
          height={260}
        >
          <HealthDistributionChart data={healthList.data ?? []} />
        </ChartCard>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr' },
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
            Top Healthy Customers
          </Typography>
          <DataTable<CustomerHealthListItem>
            columns={[
              { key: 'name', label: 'Customer', render: (r) => r.name },
              { key: 'state', label: 'State', render: (r) => r.state },
              {
                key: 'health_score',
                label: 'Health Score',
                render: (r) => <HealthScoreBar score={r.health_score} status={r.health_status} />,
              },
              { key: 'health_status', label: 'Risk', render: (r) => <StatusChip value={r.health_status} /> },
            ]}
            rows={healthyCustomers.data ?? []}
            getRowKey={(r) => r.college_id}
            loading={healthyCustomers.isLoading}
            error={healthyCustomers.isError}
            onRetry={() => healthyCustomers.refetch()}
            onRowClick={(r) => navigate(`/customers/${r.college_id}`)}
            emptyDescription="No healthy customers yet — run a health score recalculation."
            dense
          />
        </Box>

        <Box>
          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
            Critical Customers
          </Typography>
          <DataTable<CustomerHealthListItem>
            columns={[
              { key: 'name', label: 'Customer', render: (r) => r.name },
              { key: 'state', label: 'State', render: (r) => r.state },
              {
                key: 'health_score',
                label: 'Health Score',
                render: (r) => <HealthScoreBar score={r.health_score} status={r.health_status} />,
              },
              { key: 'health_status', label: 'Risk', render: (r) => <StatusChip value={r.health_status} /> },
            ]}
            rows={criticalCustomers.data ?? []}
            getRowKey={(r) => r.college_id}
            loading={criticalCustomers.isLoading}
            error={criticalCustomers.isError}
            onRetry={() => criticalCustomers.refetch()}
            onRowClick={(r) => navigate(`/customers/${r.college_id}`)}
            emptyDescription="No critical customers right now."
            dense
          />
        </Box>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography variant="h6" fontWeight={600}>
          Top Sales Opportunities
        </Typography>
        <Button size="small" onClick={() => navigate('/sales-opportunities')}>
          View all opportunities
        </Button>
      </Box>
      <Box sx={{ mb: 3 }}>
        <DataTable<CustomerPrediction>
          columns={[
            { key: 'name', label: 'Customer', render: (r) => r.name },
            { key: 'state', label: 'State', render: (r) => r.state },
            {
              key: 'purchase_probability',
              label: 'Purchase Probability',
              render: (r) => <ProbabilityBar value={r.purchase_probability} />,
            },
            {
              key: 'expected_order_value',
              label: 'Expected Order Value',
              align: 'right',
              render: (r) => formatCurrency(r.expected_order_value),
            },
            {
              key: 'expected_revenue',
              label: 'Expected Revenue',
              align: 'right',
              render: (r) => formatCurrency(r.expected_revenue),
            },
          ]}
          rows={topOpportunities.data ?? []}
          getRowKey={(r) => r.college_id}
          loading={topOpportunities.isLoading}
          error={topOpportunities.isError}
          onRetry={() => topOpportunities.refetch()}
          onRowClick={(r) => navigate(`/customers/${r.college_id}`)}
          emptyDescription="No predictions yet — retrain the models from the Sales Opportunities page."
          dense
        />
      </Box>

      <Box>
        <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
          Recent Orders
        </Typography>
        <DataTable<RecentOrder>
          columns={[
            { key: 'order_number', label: 'Order #', render: (r) => r.order_number },
            { key: 'college_name', label: 'Customer', render: (r) => r.college_name },
            { key: 'order_date', label: 'Date', render: (r) => formatDate(r.order_date) },
            { key: 'status', label: 'Status', render: (r) => <StatusChip value={r.status} /> },
            {
              key: 'payment_status',
              label: 'Payment',
              render: (r) => <StatusChip value={r.payment_status} />,
            },
            {
              key: 'total_amount',
              label: 'Amount',
              align: 'right',
              render: (r) => formatCurrency(r.total_amount),
            },
          ]}
          rows={recentOrders.data ?? []}
          getRowKey={(r) => r.id}
          loading={recentOrders.isLoading}
          error={recentOrders.isError}
          onRetry={() => recentOrders.refetch()}
          emptyDescription="No orders placed yet."
          dense
        />
      </Box>
    </>
  )
}
