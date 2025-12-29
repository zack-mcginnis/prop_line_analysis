import clsx from 'clsx'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  color?: 'green' | 'red' | 'blue' | 'purple' | 'yellow'
}

export default function StatCard({ title, value, subtitle, trend, color = 'green' }: StatCardProps) {
  const colorClasses = {
    green: 'from-emerald-500/20 to-emerald-900/10 border-emerald-500/30',
    red: 'from-red-500/20 to-red-900/10 border-red-500/30',
    blue: 'from-blue-500/20 to-blue-900/10 border-blue-500/30',
    purple: 'from-purple-500/20 to-purple-900/10 border-purple-500/30',
    yellow: 'from-yellow-500/20 to-yellow-900/10 border-yellow-500/30',
  }

  const textColorClasses = {
    green: 'text-emerald-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
  }

  return (
    <div className={clsx(
      'rounded-xl p-5 border bg-gradient-to-br',
      colorClasses[color]
    )}>
      <p className="text-dark-400 text-sm font-medium mb-1">{title}</p>
      <div className="flex items-baseline gap-2">
        <p className={clsx('text-3xl font-bold font-display', textColorClasses[color])}>
          {value}
        </p>
        {trend && (
          <span className={clsx(
            'text-sm',
            trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-dark-400'
          )}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="text-dark-400 text-sm mt-1">{subtitle}</p>
      )}
    </div>
  )
}

