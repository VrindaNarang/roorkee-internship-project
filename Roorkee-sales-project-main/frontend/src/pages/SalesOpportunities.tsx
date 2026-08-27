import { useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Slider,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import PaidOutlinedIcon from '@mui/icons-material/PaidOutlined'
import ReceiptLongOutlinedIcon from '@mui/icons-material/ReceiptLongOutlined'
import TrendingUpOutlinedIcon from '@mui/icons-material/TrendingUpOutlined'
import { useNavigate } from 'react-router-dom'
import { KpiCard } from '../components/dashboard/KpiCard'
import { ChartCard } from '../components/charts/ChartCard'
import { RankedBarChart } from '../components/charts/RankedBarChart'
import { FEATURE_LABELS } from '../components/charts/ContributionChart'
import { DataTable } from '../components/table/DataTable'
import { StatusChip } from '../components/common/StatusChip'
import { PageIntro } from '../components/common/PageIntro'
import { SelectFilter } from '../components/filters/SelectFilter'
import { FilterBar } from '../components/filters/FilterBar'
import { ProbabilityBar } from '../components/predictions/ProbabilityBar'
import { useCustomerPredictions, useRetrainModels } from '../hooks/usePredictionQueries'
import { useCustomerStates } from '../hooks/useCustomerQueries'
import { useTopFeatures } from '../hooks/useExplainabilityQueries'
import { useAuth } from '../context/AuthContext'
import { formatCurrency, formatDate, formatNumber } from '../utils/format'
import type { CustomerPrediction } from '../api/types'

// Mirrors the backend's `require_role("admin", "sales_manager")` on
// `POST /ml/retrain` (see `app/api/v1/routers/ml_admin.py`) — a
// sales_executive would get a 403 from the API, so the button is disabled
// here too rather than letting them click it and hit an error.
const CAN_RETRAIN_ROLES = ['admin', 'sales_manager']

const INSTITUTION_TYPE_OPTIONS = [
  { value: 'government', label: 'Government' },
  { value: 'private', label: 'Private' },
  { value: 'university', label: 'University' },
  { value: 'research_lab', label: 'Research Lab' },
  { value: 'industry', label: 'Industry' },
]

interface RankedPrediction extends CustomerPrediction {
  rank: number
}

export default function SalesOpportunities() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [state, setState] = useState('')
  const [institutionType, setInstitutionType] = useState('')
  const [minProbability, setMinProbability] = useState(0)
  const [minExpectedRevenue, setMinExpectedRevenue] = useState('')

  const canRetrain = Boolean(user && CAN_RETRAIN_ROLES.includes(user.role))
  const states = useCustomerStates()
  const retrain = useRetrainModels()
  const featureImportance = useTopFeatures('purchase_probability', 10)

  const params = useMemo(
    () => ({
      state: state || undefined,
      institution_type: institutionType || undefined,
      min_probability: minProbability > 0 ? minProbability : undefined,
      min_expected_revenue: minExpectedRevenue ? Number(minExpectedRevenue) : undefined,
    }),
    [state, institutionType, minProbability, minExpectedRevenue],
  )

  const predictions = useCustomerPredictions(params)

  const ranked: RankedPrediction[] = (predictions.data ?? []).map((p, i) => ({ ...p, rank: i + 1 }))

  const totalExpectedRevenue = ranked.reduce((sum, p) => sum + p.expected_revenue, 0)
  const avgProbability = ranked.length
    ? ranked.reduce((sum, p) => sum + p.purchase_probability, 0) / ranked.length
    : 0

  return (
    <>
      <PageIntro description="Which colleges are most likely to order in the next 30 days, and how much they're expected to spend — ranked so outreach effort goes to the highest-value opportunities first." />

      {retrain.isSuccess && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => retrain.reset()}>
          Models retrained (version {retrain.data.version}) — predictions refreshed for{' '}
          {retrain.data.predictions_written} customers.
        </Alert>
      )}
      {retrain.isError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => retrain.reset()}>
          Retraining failed. Check backend logs for details.
        </Alert>
      )}

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' },
          gap: 2,
          mb: 3,
        }}
      >
        <KpiCard
          label="Total Opportunities"
          value={formatNumber(ranked.length)}
          icon={<ReceiptLongOutlinedIcon fontSize="small" />}
          loading={predictions.isLoading}
        />
        <KpiCard
          label="Total Expected Revenue"
          value={formatCurrency(totalExpectedRevenue)}
          icon={<PaidOutlinedIcon fontSize="small" />}
          loading={predictions.isLoading}
        />
        <KpiCard
          label="Average Purchase Probability"
          value={`${avgProbability.toFixed(0)}%`}
          icon={<TrendingUpOutlinedIcon fontSize="small" />}
          loading={predictions.isLoading}
        />
      </Box>

      <Box sx={{ mb: 3 }}>
        <ChartCard
          title="What's Driving Purchase Likelihood"
          subtitle="Mean absolute SHAP contribution per feature, across every current prediction"
          loading={featureImportance.isLoading}
          error={featureImportance.isError}
          onRetry={() => featureImportance.refetch()}
          isEmpty={(featureImportance.data?.top_features ?? []).length === 0}
          height={280}
        >
          <RankedBarChart
            data={(featureImportance.data?.top_features ?? []).map((f) => ({
              ...f,
              label: FEATURE_LABELS[f.feature] ?? f.feature,
            }))}
            categoryKey="label"
            valueKey="mean_abs_contribution"
            limit={10}
            valueFormatter={(v) => v.toFixed(2)}
            tooltipRows={(point) => [{ label: 'Mean |contribution|', value: point.mean_abs_contribution.toFixed(3) }]}
            tooltipLabel={(point) => point.label}
          />
        </ChartCard>
      </Box>

      <FilterBar
        action={
          <Tooltip title={canRetrain ? '' : 'Only Admins and Sales Managers can retrain models'}>
            <span>
              <Button
                variant="outlined"
                startIcon={<RefreshRoundedIcon />}
                onClick={() => retrain.mutate()}
                disabled={retrain.isPending || !canRetrain}
              >
                {retrain.isPending ? 'Retraining…' : 'Retrain Models'}
              </Button>
            </span>
          </Tooltip>
        }
      >
        <SelectFilter
          label="State"
          value={state}
          onChange={setState}
          options={(states.data ?? []).map((s) => ({ value: s, label: s }))}
        />
        <SelectFilter
          label="Customer Type"
          value={institutionType}
          onChange={setInstitutionType}
          options={INSTITUTION_TYPE_OPTIONS}
        />
        <Box sx={{ width: 200, px: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Min. Probability: {minProbability}%
          </Typography>
          <Slider
            size="small"
            value={minProbability}
            onChange={(_, v) => setMinProbability(v as number)}
            min={0}
            max={100}
            step={5}
          />
        </Box>
        <TextField
          label="Min. Expected Revenue (₹)"
          size="small"
          type="number"
          value={minExpectedRevenue}
          onChange={(e) => setMinExpectedRevenue(e.target.value)}
          sx={{ width: 200 }}
        />
      </FilterBar>

      <DataTable<RankedPrediction>
        columns={[
          { key: 'rank', label: '#', render: (r) => `#${r.rank}` },
          { key: 'name', label: 'Customer', render: (r) => r.name },
          { key: 'state', label: 'State', render: (r) => r.state },
          {
            key: 'institution_type',
            label: 'Type',
            render: (r) => <StatusChip value={r.institution_type} />,
          },
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
          {
            key: 'confidence_score',
            label: 'Confidence',
            align: 'right',
            render: (r) => `${r.confidence_score.toFixed(0)}%`,
          },
          {
            key: 'prediction_date',
            label: 'Predicted',
            render: (r) => formatDate(r.prediction_date),
          },
        ]}
        rows={ranked}
        getRowKey={(r) => r.college_id}
        loading={predictions.isLoading}
        error={predictions.isError}
        onRetry={() => predictions.refetch()}
        onRowClick={(r) => navigate(`/customers/${r.college_id}`)}
        emptyTitle="No opportunities match these filters"
        emptyDescription="Try loosening the probability or revenue filters, or retrain the models if none have run yet."
        skeletonRows={8}
      />
    </>
  )
}
