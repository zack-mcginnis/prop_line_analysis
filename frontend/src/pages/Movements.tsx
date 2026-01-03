import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import clsx from 'clsx'
import { getMovements, triggerDetection } from '../api/client'

export default function Movements() {
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState({
    player_name: '',
    prop_type: '',
    min_movement_pct: '',
    went_under: '',
    page: 1,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['movements', filters],
    queryFn: () => getMovements({
      player_name: filters.player_name || undefined,
      prop_type: filters.prop_type || undefined,
      min_movement_pct: filters.min_movement_pct ? parseFloat(filters.min_movement_pct) : undefined,
      went_under: filters.went_under === 'true' ? true : filters.went_under === 'false' ? false : undefined,
      page: filters.page,
      page_size: 20,
    }),
  })

  const detectMutation = useMutation({
    mutationFn: triggerDetection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['movements'] })
    },
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl text-white">Line Movements</h1>
          <p className="text-dark-400 mt-1">
            Significant prop line drops detected before game time
          </p>
        </div>
        <button
          onClick={() => detectMutation.mutate({})}
          disabled={detectMutation.isPending}
          className="btn btn-primary"
        >
          {detectMutation.isPending ? 'Running...' : 'Run Detection'}
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Player Name</label>
            <input
              type="text"
              placeholder="Search player..."
              value={filters.player_name}
              onChange={(e) => setFilters({ ...filters, player_name: e.target.value, page: 1 })}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white placeholder-dark-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Prop Type</label>
            <select
              value={filters.prop_type}
              onChange={(e) => setFilters({ ...filters, prop_type: e.target.value, page: 1 })}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="">All Types</option>
              <option value="rushing_yards">Rushing Yards</option>
              <option value="receiving_yards">Receiving Yards</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Min Movement %</label>
            <input
              type="number"
              placeholder="e.g., 10"
              value={filters.min_movement_pct}
              onChange={(e) => setFilters({ ...filters, min_movement_pct: e.target.value, page: 1 })}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white placeholder-dark-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Result</label>
            <select
              value={filters.went_under}
              onChange={(e) => setFilters({ ...filters, went_under: e.target.value, page: 1 })}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="">All Results</option>
              <option value="true">Went Under</option>
              <option value="false">Went Over</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="card overflow-hidden p-0">
        {isLoading ? (
          <div className="p-8 text-center text-dark-400">Loading movements...</div>
        ) : !data?.items.length ? (
          <div className="p-8 text-center text-dark-400">
            No movements found. Run detection to populate data.
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-dark-900 border-b border-dark-700">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Player
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Prop
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Line Movement
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      % Change
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Hours Before
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Result
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-dark-400 uppercase tracking-wider">
                      Game Date
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-700">
                  {data.items.map((movement) => (
                    <tr key={movement.id} className="hover:bg-dark-800/50 transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-medium text-white">{movement.player_name}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="badge badge-info">
                          {movement.prop_type === 'rushing_yards' ? 'Rush' : 'Rec'} Yds
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-dark-300">
                          {movement.initial_line} → {movement.final_line}
                        </span>
                        <span className="text-red-400 ml-2">
                          ({movement.movement_absolute > 0 ? '+' : ''}{movement.movement_absolute.toFixed(1)})
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={clsx(
                          'font-mono',
                          movement.movement_pct < 0 ? 'text-red-400' : 'text-emerald-400'
                        )}>
                          {movement.movement_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-dark-300">
                        {movement.hours_before_kickoff.toFixed(1)}h
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {movement.actual_yards !== null ? (
                          <div>
                            <span className={clsx(
                              'badge',
                              movement.went_under ? 'badge-success' : 'badge-danger'
                            )}>
                              {movement.went_under ? 'Under' : 'Over'}
                            </span>
                            <span className="text-dark-400 text-sm ml-2">
                              ({movement.actual_yards} yds)
                            </span>
                          </div>
                        ) : (
                          <span className="text-dark-500">Pending</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-dark-400 text-sm">
                        {format(new Date(movement.game_commence_time), 'MMM d, yyyy')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-dark-700 bg-dark-900">
              <p className="text-sm text-dark-400">
                Showing {data.items.length} of {data.total} movements
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
                  disabled={filters.page === 1}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
                  disabled={data.items.length < 20}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

