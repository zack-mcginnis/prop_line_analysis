import { useQuery } from '@tanstack/react-query'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts'
import StatCard from '../components/StatCard'
import ThesisCard from '../components/ThesisCard'
import { getThesisSummary, getMovementSummary, getAnalysisResults } from '../api/client'

const COLORS = ['#10b981', '#ef4444', '#6b7280']

export default function Dashboard() {
  const { data: thesis, isLoading: thesisLoading } = useQuery({
    queryKey: ['thesis'],
    queryFn: getThesisSummary,
  })

  const { data: summary } = useQuery({
    queryKey: ['movementSummary'],
    queryFn: () => getMovementSummary({ min_movement_pct: 10 }),
  })

  const { data: results } = useQuery({
    queryKey: ['analysisResults'],
    queryFn: () => getAnalysisResults(),
  })

  // Prepare chart data
  const pieData = summary ? [
    { name: 'Under', value: summary.under_count },
    { name: 'Over', value: summary.over_count },
    { name: 'Push', value: summary.with_results - summary.under_count - summary.over_count },
  ] : []

  const barData = results
    ?.filter(r => r.analysis_name.includes('all'))
    .map(r => ({
      name: `${r.movement_threshold_pct}%/${r.hours_before_threshold}h`,
      under: r.under_rate * 100,
      over: r.over_rate * 100,
      sample: r.sample_size,
    })) || []

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl text-white">Dashboard</h1>
          <p className="text-dark-400 mt-1">NFL Player Prop Line Movement Analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-info">
            {summary?.total_movements || 0} Movements Tracked
          </span>
        </div>
      </div>

      {/* Thesis Validation Card */}
      {thesisLoading ? (
        <div className="card animate-pulse h-64 flex items-center justify-center">
          <p className="text-dark-400">Loading thesis analysis...</p>
        </div>
      ) : thesis ? (
        <ThesisCard data={thesis} />
      ) : (
        <div className="card text-center py-8">
          <p className="text-dark-400 mb-4">No analysis results yet.</p>
          <p className="text-sm text-dark-500">Run the analysis to validate the thesis.</p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Movements"
          value={summary?.total_movements || 0}
          subtitle="Significant line drops detected"
          color="blue"
        />
        <StatCard
          title="With Results"
          value={summary?.with_results || 0}
          subtitle="Games completed"
          color="purple"
        />
        <StatCard
          title="Under Rate"
          value={summary?.under_rate ? `${(summary.under_rate * 100).toFixed(1)}%` : 'N/A'}
          subtitle="Of players went under"
          color="green"
          trend={summary?.under_rate && summary.under_rate > 0.5 ? 'up' : 'neutral'}
        />
        <StatCard
          title="Over Rate"
          value={summary?.over_rate ? `${(summary.over_rate * 100).toFixed(1)}%` : 'N/A'}
          subtitle="Of players went over"
          color="red"
          trend={summary?.over_rate && summary.over_rate > 0.5 ? 'up' : 'neutral'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Over/Under Distribution */}
        <div className="card">
          <h3 className="font-display font-semibold text-lg text-white mb-4">
            Over/Under Distribution
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a2235',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-dark-400">
              No data available
            </div>
          )}
        </div>

        {/* Threshold Comparison */}
        <div className="card">
          <h3 className="font-display font-semibold text-lg text-white mb-4">
            Under Rate by Threshold
          </h3>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={{ stroke: '#334155' }}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a2235',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number) => `${value.toFixed(1)}%`}
                />
                <Bar dataKey="under" name="Under Rate" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-dark-400">
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Recent Movements Preview */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-semibold text-lg text-white">
            How It Works
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-dark-900/50 rounded-lg p-4 border border-dark-700">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center mb-3">
              <span className="text-blue-400 text-xl">1</span>
            </div>
            <h4 className="font-semibold text-white mb-2">Collect Data</h4>
            <p className="text-dark-400 text-sm">
              Scrape prop lines from multiple sportsbooks leading up to each game, 
              tracking changes over time.
            </p>
          </div>
          <div className="bg-dark-900/50 rounded-lg p-4 border border-dark-700">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center mb-3">
              <span className="text-purple-400 text-xl">2</span>
            </div>
            <h4 className="font-semibold text-white mb-2">Detect Movements</h4>
            <p className="text-dark-400 text-sm">
              Identify significant line drops (≥10% or ≥5 yards) that occur 
              within 3 hours of kickoff.
            </p>
          </div>
          <div className="bg-dark-900/50 rounded-lg p-4 border border-dark-700">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center mb-3">
              <span className="text-emerald-400 text-xl">3</span>
            </div>
            <h4 className="font-semibold text-white mb-2">Analyze Correlation</h4>
            <p className="text-dark-400 text-sm">
              Compare actual player performance against the final line to 
              calculate over/under rates.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

