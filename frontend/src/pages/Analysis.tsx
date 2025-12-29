import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, Legend
} from 'recharts'
import clsx from 'clsx'
import { getAnalysisResults, getAnalysisComparison, triggerAnalysis } from '../api/client'

export default function Analysis() {
  const queryClient = useQueryClient()

  const { data: results, isLoading } = useQuery({
    queryKey: ['analysisResults'],
    queryFn: () => getAnalysisResults(),
  })

  const { data: comparison } = useQuery({
    queryKey: ['analysisComparison'],
    queryFn: () => getAnalysisComparison(),
  })

  const analysisMutation = useMutation({
    mutationFn: triggerAnalysis,
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['analysisResults'] })
        queryClient.invalidateQueries({ queryKey: ['analysisComparison'] })
        queryClient.invalidateQueries({ queryKey: ['thesis'] })
      }, 5000)
    },
  })

  // Filter results for "all" prop types for the main comparison
  const allPropResults = results?.filter(r => !r.prop_type) || []
  
  // Prepare bar chart data
  const barData = allPropResults.map(r => ({
    name: `${r.movement_threshold_pct}%/${r.hours_before_threshold}h`,
    under: r.under_rate * 100,
    over: r.over_rate * 100,
    sample: r.sample_size,
    significant: r.is_significant,
  }))

  // Prepare scatter data for threshold exploration
  const scatterData = results?.map(r => ({
    pct: r.movement_threshold_pct,
    hours: r.hours_before_threshold,
    underRate: r.under_rate * 100,
    sample: r.sample_size,
    significant: r.is_significant,
    name: r.analysis_name,
  })) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl text-white">Analysis</h1>
          <p className="text-dark-400 mt-1">
            Statistical analysis of line movements and outcomes
          </p>
        </div>
        <button
          onClick={() => analysisMutation.mutate()}
          disabled={analysisMutation.isPending}
          className="btn btn-primary"
        >
          {analysisMutation.isPending ? 'Running...' : 'Run Analysis'}
        </button>
      </div>

      {/* Best Threshold Card */}
      {comparison?.best_threshold && (
        <div className="card bg-gradient-to-br from-emerald-900/30 to-dark-900 border-emerald-500/40">
          <h3 className="font-display font-semibold text-lg text-white mb-2">
            Best Threshold Configuration
          </h3>
          <p className="text-dark-300 mb-4">{comparison.recommendation}</p>
          <div className="grid grid-cols-4 gap-4">
            <div>
              <p className="text-dark-400 text-sm">Movement %</p>
              <p className="text-2xl font-bold text-emerald-400">
                {comparison.best_threshold.thresholds.pct}%
              </p>
            </div>
            <div>
              <p className="text-dark-400 text-sm">Absolute</p>
              <p className="text-2xl font-bold text-emerald-400">
                {comparison.best_threshold.thresholds.abs} yds
              </p>
            </div>
            <div>
              <p className="text-dark-400 text-sm">Time Window</p>
              <p className="text-2xl font-bold text-emerald-400">
                {comparison.best_threshold.thresholds.hours}h
              </p>
            </div>
            <div>
              <p className="text-dark-400 text-sm">Under Rate</p>
              <p className="text-2xl font-bold text-emerald-400">
                {comparison.best_threshold.under_rate.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Threshold Comparison Chart */}
        <div className="card">
          <h3 className="font-display font-semibold text-lg text-white mb-4">
            Under Rate by Threshold (All Props)
          </h3>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: '#334155' }}
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={{ stroke: '#334155' }}
                  domain={[0, 100]}
                  label={{ value: '%', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a2235',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => [
                    `${value.toFixed(1)}%`,
                    name === 'under' ? 'Under Rate' : 'Over Rate'
                  ]}
                />
                <Legend />
                <Bar dataKey="under" name="Under" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="over" name="Over" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-dark-400">
              No data available. Run analysis first.
            </div>
          )}
        </div>

        {/* Sample Size Distribution */}
        <div className="card">
          <h3 className="font-display font-semibold text-lg text-white mb-4">
            Statistical Significance
          </h3>
          {scatterData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="pct" 
                  name="Movement %" 
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={{ stroke: '#334155' }}
                  label={{ value: 'Movement %', position: 'bottom', fill: '#94a3b8' }}
                />
                <YAxis
                  dataKey="underRate"
                  name="Under Rate"
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                  axisLine={{ stroke: '#334155' }}
                  domain={[40, 70]}
                  label={{ value: 'Under %', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                />
                <ZAxis dataKey="sample" range={[50, 400]} name="Sample Size" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a2235',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                  formatter={(value: number, name: string) => {
                    if (name === 'Under Rate') return `${value.toFixed(1)}%`
                    if (name === 'Movement %') return `${value}%`
                    return value
                  }}
                />
                <Legend />
                <Scatter 
                  name="Significant" 
                  data={scatterData.filter(d => d.significant)} 
                  fill="#10b981"
                />
                <Scatter 
                  name="Not Significant" 
                  data={scatterData.filter(d => !d.significant)} 
                  fill="#6b7280"
                />
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-dark-400">
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Results Table */}
      <div className="card overflow-hidden p-0">
        <div className="p-4 border-b border-dark-700">
          <h3 className="font-display font-semibold text-lg text-white">
            All Analysis Results
          </h3>
        </div>
        {isLoading ? (
          <div className="p-8 text-center text-dark-400">Loading...</div>
        ) : !results?.length ? (
          <div className="p-8 text-center text-dark-400">
            No analysis results. Click "Run Analysis" to generate.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Analysis
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Prop Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Thresholds
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Sample
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Under Rate
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    P-Value
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase">
                    Significant
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {results.map((result) => (
                  <tr key={result.id} className="hover:bg-dark-800/50">
                    <td className="px-4 py-3 text-sm text-white">
                      {result.analysis_name.split('_').slice(1).join(' ')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="badge badge-info">
                        {result.prop_type || 'All'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-dark-300">
                      {result.movement_threshold_pct}% / {result.movement_threshold_abs}yds / {result.hours_before_threshold}h
                    </td>
                    <td className="px-4 py-3 text-sm text-dark-300">
                      {result.sample_size}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'font-mono font-medium',
                        result.under_rate * 100 > 55 ? 'text-emerald-400' : 
                        result.under_rate * 100 > 50 ? 'text-yellow-400' : 'text-dark-400'
                      )}>
                        {(result.under_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-dark-300">
                      {result.p_value?.toFixed(4) || 'N/A'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'badge',
                        result.is_significant ? 'badge-success' : 'badge-warning'
                      )}>
                        {result.is_significant ? 'Yes' : 'No'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

