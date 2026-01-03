import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useMemo, useEffect } from 'react'
import { getDashboardView, LineChangeData, connectDashboardWebSocket, disconnectDashboardWebSocket } from '../api/client'

type SortField = 'player' | 'current' | 'm5' | 'm10' | 'm15' | 'm30' | 'm45' | 'm60' | 'h12' | 'h24' | 'sinceOpen'
type SortDirection = 'asc' | 'desc'

export default function Dashboard() {
  const [sortField, setSortField] = useState<SortField>('m5')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [propTypeFilter, setPropTypeFilter] = useState<'all' | 'rushing_yards' | 'receiving_yards'>('all')
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date())
  const queryClient = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dashboardView', propTypeFilter],
    queryFn: async () => {
      const result = await getDashboardView({ 
        prop_type: propTypeFilter === 'all' ? undefined : propTypeFilter,
        hours_back: 48 
      })


      
      return result
    },
    refetchInterval: 30000, // Fallback: Refresh every 30 seconds (WebSocket is primary)
  })

  // Establish WebSocket connection for real-time updates
  useEffect(() => {
    connectDashboardWebSocket(
      (wsData) => {
        console.log('📨 Received WebSocket update:', wsData)
        console.log(`📊 Total items: ${wsData.total}`)

        // Update the query cache with new data
        queryClient.setQueryData(['dashboardView', propTypeFilter], wsData)
        
        // Update last update time
        setLastUpdateTime(new Date())
      },
      (error) => {
        console.error('WebSocket error:', error)
      },
      () => {
        console.log('WebSocket closed, will attempt reconnect...')
        // React Query will handle fallback polling
      }
    )

    // Cleanup on unmount
    return () => {
      disconnectDashboardWebSocket()
    }
  }, [queryClient, propTypeFilter])

  const propLineData = data?.items || []

  const filteredAndSortedData = useMemo(() => {
    // Note: prop_type filtering is now done by the API
    const filtered = propLineData

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: number | null = null
      let bVal: number | null = null

      switch (sortField) {
        case 'player':
          return sortDirection === 'asc' 
            ? a.player_name.localeCompare(b.player_name)
            : b.player_name.localeCompare(a.player_name)
        case 'current':
          aVal = a.current_line
          bVal = b.current_line
          break
        case 'm5':
          aVal = a.m5.percent
          bVal = b.m5.percent
          break
        case 'm10':
          aVal = a.m10.percent
          bVal = b.m10.percent
          break
        case 'm15':
          aVal = a.m15.percent
          bVal = b.m15.percent
          break
        case 'm30':
          aVal = a.m30.percent
          bVal = b.m30.percent
          break
        case 'm45':
          aVal = a.m45.percent
          bVal = b.m45.percent
          break
        case 'm60':
          aVal = a.m60.percent
          bVal = b.m60.percent
          break
        case 'h12':
          aVal = a.h12.percent
          bVal = b.h12.percent
          break
        case 'h24':
          aVal = a.h24.percent
          bVal = b.h24.percent
          break
        case 'sinceOpen':
          aVal = a.since_open.percent
          bVal = b.since_open.percent
          break
      }

      if (aVal === null && bVal === null) return 0
      if (aVal === null) return 1
      if (bVal === null) return -1

      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return sorted
  }, [propLineData, sortField, sortDirection])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection(field === 'player' ? 'asc' : 'desc')
    }
  }

  const formatChange = (change: LineChangeData): JSX.Element => {
    if (change.absolute === null || change.percent === null || change.old_line === null) {
      return <span className="text-dark-500 text-sm">—</span>
    }

    const isNegative = change.absolute < 0
    const isSignificant = Math.abs(change.percent) >= 5

    const colorClass = isNegative 
      ? isSignificant ? 'text-red-400' : 'text-red-500/60'
      : isSignificant ? 'text-emerald-400' : 'text-emerald-500/60'

    const bgClass = isSignificant
      ? isNegative ? 'bg-red-500/10' : 'bg-emerald-500/10'
      : ''

    const arrow = isNegative ? '↓' : '↑'
    const formatOdds = (odds: number | null) => odds ? (odds > 0 ? `+${odds}` : `${odds}`) : ''

    return (
      <div className={`${bgClass} rounded px-2 py-1.5 text-xs`}>
        {/* From label and old line/odds */}
        <div className="text-dark-400 font-mono mb-1 flex items-center justify-center gap-1">
          <span className="text-dark-500 text-[10px]">From</span>
          <span>{change.old_line.toFixed(1)}</span>
          {(change.old_over_odds || change.old_under_odds) && (
            <span className="text-dark-500 text-[10px] flex flex-col items-start">
              {change.old_over_odds && <span>O:{formatOdds(change.old_over_odds)}</span>}
              {change.old_under_odds && <span>U:{formatOdds(change.old_under_odds)}</span>}
            </span>
          )}
        </div>
        
        {/* Arrow and change */}
        <div className={`font-medium ${colorClass} flex items-center justify-center gap-1`}>
          <span className="text-base">{arrow}</span>
          <span>{Math.abs(change.absolute).toFixed(1)} ({Math.abs(change.percent).toFixed(1)}%)</span>
        </div>
      </div>
    )
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <span className="text-dark-600">⇅</span>
    }
    return sortDirection === 'asc' ? <span className="text-blue-400">↑</span> : <span className="text-blue-400">↓</span>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl text-white">Line Movement Dashboard</h1>
          <p className="text-dark-400 mt-1">Track prop line changes across time windows</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="badge badge-info">
            {propLineData.length} Active Props
          </span>
          <button
            onClick={() => refetch()}
            className="btn btn-sm btn-secondary"
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex items-center gap-4">
          <span className="text-sm text-dark-400">Prop Type:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPropTypeFilter('all')}
              className={`btn btn-sm ${propTypeFilter === 'all' ? 'btn-primary' : 'btn-ghost'}`}
            >
              All ({propLineData.length})
            </button>
            <button
              onClick={() => setPropTypeFilter('rushing_yards')}
              className={`btn btn-sm ${propTypeFilter === 'rushing_yards' ? 'btn-primary' : 'btn-ghost'}`}
            >
              Rushing ({propLineData.filter(p => p.prop_type === 'rushing_yards').length})
            </button>
            <button
              onClick={() => setPropTypeFilter('receiving_yards')}
              className={`btn btn-sm ${propTypeFilter === 'receiving_yards' ? 'btn-primary' : 'btn-ghost'}`}
            >
              Receiving ({propLineData.filter(p => p.prop_type === 'receiving_yards').length})
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-dark-400">Loading prop data...</p>
            </div>
          </div>
        ) : filteredAndSortedData.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-dark-400 mb-4">No prop data available</p>
            <p className="text-sm text-dark-500">Load mock data or start scraping to see line movements</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-dark-900/50 border-b border-dark-700">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <button
                      onClick={() => handleSort('player')}
                      className="flex items-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors"
                    >
                      Player
                      <SortIcon field="player" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('current')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Current
                      <SortIcon field="current" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m5')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 5min
                      <SortIcon field="m5" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m10')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 10min
                      <SortIcon field="m10" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m15')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 15min
                      <SortIcon field="m15" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m30')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 30min
                      <SortIcon field="m30" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m45')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 45min
                      <SortIcon field="m45" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('m60')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 60min
                      <SortIcon field="m60" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('h12')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 12 Hour
                      <SortIcon field="h12" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('h24')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Last 24 Hour
                      <SortIcon field="h24" />
                    </button>
                  </th>
                  <th className="px-4 py-3 text-center">
                    <button
                      onClick={() => handleSort('sinceOpen')}
                      className="flex items-center justify-center gap-2 text-dark-300 hover:text-white text-sm font-medium transition-colors w-full"
                    >
                      Since Open
                      <SortIcon field="sinceOpen" />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {filteredAndSortedData.map((item, index) => (
                  <tr key={`${item.player_name}_${item.prop_type}_${index}`} className="hover:bg-dark-900/30 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-medium text-white">{item.player_name}</div>
                        <div className="text-xs text-dark-400 capitalize">
                          {item.prop_type.replace('_', ' ')}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2 font-mono">
                        <span className="text-lg font-semibold text-white">
                          {item.current_line ? item.current_line.toFixed(1) : '—'}
                        </span>
                        <span className="text-xs text-dark-400 flex flex-col items-start">
                          {item.current_over_odds && (
                            <span>
                              <span className="text-dark-500">O:</span>{item.current_over_odds > 0 ? `+${item.current_over_odds}` : item.current_over_odds}
                            </span>
                          )}
                          {item.current_under_odds && (
                            <span>
                              <span className="text-dark-500">U:</span>{item.current_under_odds > 0 ? `+${item.current_under_odds}` : item.current_under_odds}
                            </span>
                          )}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m5)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m10)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m15)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m30)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m45)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.m60)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.h12)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.h24)}</td>
                    <td className="px-4 py-3 text-center">{formatChange(item.since_open)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="card bg-dark-900/50">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-red-500/20 border border-red-500/50"></div>
              <span className="text-dark-400">Significant Drop (≥5%)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-emerald-500/20 border border-emerald-500/50"></div>
              <span className="text-dark-400">Significant Increase (≥5%)</span>
            </div>
          </div>
          <div className="text-dark-500 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Last updated: {lastUpdateTime.toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  )
}
