import clsx from 'clsx'
import type { ThesisSummary } from '../api/client'

interface ThesisCardProps {
  data: ThesisSummary
}

export default function ThesisCard({ data }: ThesisCardProps) {
  return (
    <div className={clsx(
      'rounded-xl p-6 border',
      data.is_supported 
        ? 'bg-gradient-to-br from-emerald-900/30 to-emerald-950/20 border-emerald-500/40 glow-green'
        : data.under_rate > 50 
          ? 'bg-gradient-to-br from-yellow-900/30 to-yellow-950/20 border-yellow-500/40'
          : 'bg-gradient-to-br from-red-900/30 to-red-950/20 border-red-500/40 glow-red'
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="font-display font-bold text-xl text-white mb-1">Thesis Validation</h2>
          <p className="text-dark-400 text-sm">{data.thesis}</p>
        </div>
        <span className={clsx(
          'badge',
          data.is_supported ? 'badge-success' : data.under_rate > 50 ? 'badge-warning' : 'badge-danger'
        )}>
          {data.is_supported ? 'Supported' : data.under_rate > 50 ? 'Trending' : 'Not Supported'}
        </span>
      </div>

      {/* Key Finding */}
      <div className="bg-dark-900/50 rounded-lg p-4 mb-4 border border-dark-700">
        <p className="text-sm text-dark-300 mb-2">Key Finding</p>
        <p className="text-white font-medium">{data.key_finding}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <p className="text-2xl font-bold font-display text-emerald-400">{data.under_rate.toFixed(1)}%</p>
          <p className="text-dark-400 text-xs">Under Rate</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold font-display text-red-400">{data.over_rate.toFixed(1)}%</p>
          <p className="text-dark-400 text-xs">Over Rate</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold font-display text-blue-400">{data.sample_size}</p>
          <p className="text-dark-400 text-xs">Sample Size</p>
        </div>
        <div className="text-center">
          <p className={clsx(
            'text-2xl font-bold font-display',
            data.is_significant ? 'text-emerald-400' : 'text-dark-400'
          )}>
            {data.p_value ? data.p_value.toFixed(4) : 'N/A'}
          </p>
          <p className="text-dark-400 text-xs">P-Value</p>
        </div>
      </div>

      {/* Conclusion */}
      <div className="border-t border-dark-700 pt-4">
        <p className="text-sm text-dark-300 mb-2">Conclusion</p>
        <p className="text-white text-sm">{data.conclusion}</p>
      </div>

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div className="mt-4 pt-4 border-t border-dark-700">
          <p className="text-sm text-dark-300 mb-2">Recommendations</p>
          <ul className="space-y-1">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="text-sm text-dark-200 flex items-start gap-2">
                <span className="text-emerald-400">•</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

