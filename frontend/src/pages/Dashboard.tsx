import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useMemo, useEffect, useRef } from 'react'
import { getDashboardView, LineChangeData, PropDashboardItem, SportsbookData, connectDashboardWebSocket, disconnectDashboardWebSocket } from '../api/client'

type SortField = 'player' | 'current' | 'm5' | 'm10' | 'm15' | 'm30' | 'm45' | 'm60' | 'h12' | 'h24' | 'sinceOpen'
type SortDirection = 'asc' | 'desc'
type Sportsbook = 'consensus' | 'draftkings' | 'fanduel' | 'betmgm' | 'caesars' | 'pointsbet'

// Type for tracking which cells have changed
type CellChanges = {
  [playerKey: string]: {
    rowChanged: boolean
    current?: boolean
    m5?: boolean
    m10?: boolean
    m15?: boolean
    m30?: boolean
    m45?: boolean
    m60?: boolean
    h12?: boolean
    h24?: boolean
    sinceOpen?: boolean
  }
}

export default function Dashboard() {
  const [sortField, setSortField] = useState<SortField>('m5')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [propTypeFilter, setPropTypeFilter] = useState<'all' | 'rushing_yards' | 'receiving_yards'>('all')
  const [playerNameFilter, setPlayerNameFilter] = useState<string>('')
  const [selectedSportsbook, setSelectedSportsbook] = useState<Sportsbook>('consensus')
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date())
  const [changedCells, setChangedCells] = useState<CellChanges>({})
  const previousDataRef = useRef<PropDashboardItem[]>([])
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

  // Helper function to get sportsbook data from an item
  const getSportsbookData = (item: PropDashboardItem, sportsbook: Sportsbook): SportsbookData | null => {
    return item[sportsbook] || null
  }

  // Detect changes when data updates
  useEffect(() => {
    if (!propLineData || propLineData.length === 0) return

    const newChanges: CellChanges = {}
    
    propLineData.forEach((newItem) => {
      const playerKey = `${newItem.player_name}_${newItem.prop_type}`
      const oldItem = previousDataRef.current.find(
        (item) => `${item.player_name}_${item.prop_type}` === playerKey
      )

      if (!oldItem) return // New item, skip change detection

      const changes: CellChanges[string] = { rowChanged: false }

      // Get sportsbook data for comparison
      const newBookData = getSportsbookData(newItem, selectedSportsbook)
      const oldBookData = getSportsbookData(oldItem, selectedSportsbook)

      if (!newBookData || !oldBookData) return

      // Check current line
      if (newBookData.current_line !== oldBookData.current_line || 
          newBookData.current_over_odds !== oldBookData.current_over_odds ||
          newBookData.current_under_odds !== oldBookData.current_under_odds) {
        changes.current = true
        changes.rowChanged = true
      }

      // Helper to check if LineChangeData has changed
      const hasLineChangeDataChanged = (newData: LineChangeData, oldData: LineChangeData) => {
        return newData.absolute !== oldData.absolute ||
               newData.percent !== oldData.percent ||
               newData.old_line !== oldData.old_line
      }

      // Check all time windows
      if (hasLineChangeDataChanged(newBookData.m5, oldBookData.m5)) {
        changes.m5 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.m10, oldBookData.m10)) {
        changes.m10 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.m15, oldBookData.m15)) {
        changes.m15 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.m30, oldBookData.m30)) {
        changes.m30 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.m45, oldBookData.m45)) {
        changes.m45 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.m60, oldBookData.m60)) {
        changes.m60 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.h12, oldBookData.h12)) {
        changes.h12 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.h24, oldBookData.h24)) {
        changes.h24 = true
        changes.rowChanged = true
      }
      if (hasLineChangeDataChanged(newBookData.since_open, oldBookData.since_open)) {
        changes.sinceOpen = true
        changes.rowChanged = true
      }

      if (changes.rowChanged) {
        newChanges[playerKey] = changes
      }
    })

    // Update changed cells state if there are any changes
    if (Object.keys(newChanges).length > 0) {
      setChangedCells(newChanges)
      
      // Clear the highlights after 3 seconds
      setTimeout(() => {
        setChangedCells({})
      }, 3000)
    }

    // Store current data as previous for next comparison
    previousDataRef.current = propLineData
  }, [propLineData, selectedSportsbook])

  const filteredAndSortedData = useMemo(() => {
    // Note: prop_type filtering is now done by the API
    // Apply player name filter and filter out items without selected sportsbook data
    const filtered = propLineData.filter(item => {
      // Filter out items that don't have data for the selected sportsbook
      if (!getSportsbookData(item, selectedSportsbook)) {
        return false
      }
      
      if (playerNameFilter) {
        return item.player_name.toLowerCase().includes(playerNameFilter.toLowerCase())
      }
      return true
    })

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let aVal: number | null = null
      let bVal: number | null = null

      const aBookData = getSportsbookData(a, selectedSportsbook)
      const bBookData = getSportsbookData(b, selectedSportsbook)

      if (!aBookData || !bBookData) return 0

      switch (sortField) {
        case 'player':
          return sortDirection === 'asc' 
            ? a.player_name.localeCompare(b.player_name)
            : b.player_name.localeCompare(a.player_name)
        case 'current':
          aVal = aBookData.current_line
          bVal = bBookData.current_line
          break
        case 'm5':
          aVal = aBookData.m5.percent
          bVal = bBookData.m5.percent
          break
        case 'm10':
          aVal = aBookData.m10.percent
          bVal = bBookData.m10.percent
          break
        case 'm15':
          aVal = aBookData.m15.percent
          bVal = bBookData.m15.percent
          break
        case 'm30':
          aVal = aBookData.m30.percent
          bVal = bBookData.m30.percent
          break
        case 'm45':
          aVal = aBookData.m45.percent
          bVal = bBookData.m45.percent
          break
        case 'm60':
          aVal = aBookData.m60.percent
          bVal = bBookData.m60.percent
          break
        case 'h12':
          aVal = aBookData.h12.percent
          bVal = bBookData.h12.percent
          break
        case 'h24':
          aVal = aBookData.h24.percent
          bVal = bBookData.h24.percent
          break
        case 'sinceOpen':
          aVal = aBookData.since_open.percent
          bVal = bBookData.since_open.percent
          break
      }

      if (aVal === null && bVal === null) return 0
      if (aVal === null) return 1
      if (bVal === null) return -1

      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return sorted
  }, [propLineData, sortField, sortDirection, playerNameFilter, selectedSportsbook])

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
      <div className={`${bgClass} rounded px-1 py-1 text-xs`}>
        {/* From label and old line/odds */}
        <div className="text-dark-400 font-mono mb-0.5 flex items-center justify-center gap-0.5">
          <span>{change.old_line.toFixed(1)}</span>
          {(change.old_over_odds || change.old_under_odds) && (
            <span className="text-dark-500 text-[10px] flex flex-col items-start">
              {change.old_over_odds && <span>O:{formatOdds(change.old_over_odds)}</span>}
              {change.old_under_odds && <span>U:{formatOdds(change.old_under_odds)}</span>}
            </span>
          )}
        </div>
        
        {/* Arrow and change */}
        <div className={`font-medium ${colorClass} flex items-center justify-center gap-0.5`}>
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

  const formatKickoffTime = (isoString: string): { date: string; time: string; isToday: boolean; isSoon: boolean } => {
    const kickoff = new Date(isoString)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const kickoffDate = new Date(kickoff.getFullYear(), kickoff.getMonth(), kickoff.getDate())
    const isToday = kickoffDate.getTime() === today.getTime()
    
    const hoursUntil = (kickoff.getTime() - now.getTime()) / (1000 * 60 * 60)
    const isSoon = hoursUntil >= 0 && hoursUntil <= 3
    
    const timeStr = kickoff.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    })
    
    // Use numeric date format (e.g. "1/4")
    const dateStr = `${kickoff.getMonth() + 1}/${kickoff.getDate()}`
    
    return { date: dateStr, time: timeStr, isToday, isSoon }
  }

  const formatPropType = (propType: string): string => {
    const typeMap: { [key: string]: string } = {
      'rushing_yards': 'Rush Yards',
      'receiving_yards': 'Rec. Yards'
    }
    return typeMap[propType] || propType.replace('_', ' ')
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
      <div className="card space-y-4">
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
        <div className="flex items-center gap-4">
          <span className="text-sm text-dark-400">Player Name:</span>
          <div className="relative flex-1 max-w-xs">
            <input
              type="text"
              placeholder="Search by player name..."
              value={playerNameFilter}
              onChange={(e) => setPlayerNameFilter(e.target.value)}
              className="w-full px-4 py-2 bg-dark-900 border border-dark-700 rounded-lg text-white placeholder-dark-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            {playerNameFilter && (
              <button
                onClick={() => setPlayerNameFilter('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white transition-colors"
                title="Clear filter"
              >
                ✕
              </button>
            )}
          </div>
          <span className="text-sm text-dark-400">Sportsbook:</span>
          <select
            value={selectedSportsbook}
            onChange={(e) => setSelectedSportsbook(e.target.value as Sportsbook)}
            className="px-4 py-2 bg-dark-900 border border-dark-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          >
            <option value="consensus">Consensus</option>
            <option value="draftkings">DraftKings</option>
            <option value="fanduel">FanDuel</option>
            <option value="betmgm">BetMGM</option>
            <option value="caesars">Caesars</option>
            <option value="pointsbet">PointsBet</option>
          </select>
          {playerNameFilter && (
            <span className="text-xs text-dark-400">
              Showing {filteredAndSortedData.length} of {propLineData.length} props
            </span>
          )}
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
            <table className="w-full" style={{ borderCollapse: 'collapse' }}>
              <thead className="bg-dark-900/50 border-b border-dark-700">
                <tr>
                  <th className="px-1.5 py-1.5 text-left">
                    <button
                      onClick={() => handleSort('player')}
                      className="flex items-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors"
                    >
                      Player
                      <SortIcon field="player" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('current')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      Current
                      <SortIcon field="current" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m5')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      5min
                      <SortIcon field="m5" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m10')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      10min
                      <SortIcon field="m10" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m15')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      15min
                      <SortIcon field="m15" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m30')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      30min
                      <SortIcon field="m30" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m45')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      45min
                      <SortIcon field="m45" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('m60')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      60min
                      <SortIcon field="m60" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('h12')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      12hr
                      <SortIcon field="h12" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('h24')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      24hr
                      <SortIcon field="h24" />
                    </button>
                  </th>
                  <th className="px-1.5 py-1.5 text-center">
                    <button
                      onClick={() => handleSort('sinceOpen')}
                      className="flex items-center justify-center gap-0.5 text-dark-300 hover:text-white text-xs font-medium transition-colors w-full"
                    >
                      Open
                      <SortIcon field="sinceOpen" />
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {filteredAndSortedData.map((item, index) => {
                  const kickoff = formatKickoffTime(item.game_commence_time)
                  const playerKey = `${item.player_name}_${item.prop_type}`
                  const cellChanges = changedCells[playerKey] || {}
                  const bookData = getSportsbookData(item, selectedSportsbook)
                  
                  if (!bookData) return null
                  
                  return (
                  <tr 
                    key={`${item.player_name}_${item.prop_type}_${index}`} 
                    className={`hover:bg-dark-900/30 transition-colors ${
                      cellChanges.rowChanged ? 'animate-row-flash' : ''
                    }`}
                  >
                    <td className="px-1.5 py-1.5">
                      <div>
                        <div className="font-medium text-white whitespace-nowrap text-sm">{item.player_name}</div>
                        <div className="text-xs text-dark-400">
                          {formatPropType(item.prop_type)}
                        </div>
                        <div className={`text-xs mt-0.5 flex items-center gap-0.5 ${
                          kickoff.isSoon ? 'text-orange-400 font-medium' : 'text-dark-500'
                        }`}>
                          <span className="whitespace-nowrap">{kickoff.date} {kickoff.time}</span>
                        </div>
                      </div>
                    </td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.current ? 'animate-cell-flash' : ''}`}>
                      <div className="flex items-center justify-center gap-1 font-mono">
                        <span className="text-base font-semibold text-white">
                          {bookData.current_line ? bookData.current_line.toFixed(1) : '—'}
                        </span>
                        <span className="text-xs text-dark-400 flex flex-col items-start">
                          {bookData.current_over_odds && (
                            <span>
                              <span className="text-dark-500">O:</span>{bookData.current_over_odds > 0 ? `+${bookData.current_over_odds}` : bookData.current_over_odds}
                            </span>
                          )}
                          {bookData.current_under_odds && (
                            <span>
                              <span className="text-dark-500">U:</span>{bookData.current_under_odds > 0 ? `+${bookData.current_under_odds}` : bookData.current_under_odds}
                            </span>
                          )}
                        </span>
                      </div>
                    </td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m5 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m5)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m10 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m10)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m15 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m15)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m30 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m30)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m45 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m45)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.m60 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.m60)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.h12 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.h12)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.h24 ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.h24)}</td>
                    <td className={`px-1.5 py-1.5 text-center ${cellChanges.sinceOpen ? 'animate-cell-flash' : ''}`}>{formatChange(bookData.since_open)}</td>
                  </tr>
                  )
                })}
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
