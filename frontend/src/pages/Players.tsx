import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getPlayers, getPropSnapshots } from '../api/client'

export default function Players() {
  const [search, setSearch] = useState('')
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null)
  const [selectedPropType, setSelectedPropType] = useState('rushing_yards')

  const { data: playersData } = useQuery({
    queryKey: ['players', search],
    queryFn: () => getPlayers(search || undefined),
    enabled: search.length >= 2,
  })

  const { data: snapshotsData, isLoading: snapshotsLoading } = useQuery({
    queryKey: ['playerSnapshots', selectedPlayer, selectedPropType],
    queryFn: () => getPropSnapshots({
      player_name: selectedPlayer || undefined,
      prop_type: selectedPropType,
      page_size: 100,
    }),
    enabled: !!selectedPlayer,
  })

  // Group snapshots by event for timeline visualization
  const eventGroups = snapshotsData?.items.reduce((acc, snap) => {
    if (!acc[snap.event_id]) {
      acc[snap.event_id] = {
        event_id: snap.event_id,
        game_commence_time: snap.game_commence_time,
        snapshots: [],
      }
    }
    acc[snap.event_id].snapshots.push({
      time: new Date(snap.snapshot_time).getTime(),
      hours: snap.hours_before_kickoff,
      consensus: snap.consensus_line,
      draftkings: snap.draftkings_line,
      fanduel: snap.fanduel_line,
    })
    return acc
  }, {} as Record<string, { event_id: string; game_commence_time: string; snapshots: any[] }>) || {}

  const events = Object.values(eventGroups).sort(
    (a, b) => new Date(b.game_commence_time).getTime() - new Date(a.game_commence_time).getTime()
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display font-bold text-3xl text-white">Players</h1>
        <p className="text-dark-400 mt-1">
          View prop line history for individual players
        </p>
      </div>

      {/* Search */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-dark-400 mb-1">Search Player</label>
            <input
              type="text"
              placeholder="Type player name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white placeholder-dark-500 focus:outline-none focus:border-emerald-500"
            />
            {playersData && search.length >= 2 && (
              <div className="mt-2 max-h-48 overflow-y-auto bg-dark-900 border border-dark-700 rounded-lg">
                {playersData.players.length === 0 ? (
                  <p className="p-3 text-dark-400 text-sm">No players found</p>
                ) : (
                  playersData.players.map((player) => (
                    <button
                      key={player}
                      onClick={() => {
                        setSelectedPlayer(player)
                        setSearch('')
                      }}
                      className="w-full text-left px-3 py-2 text-white hover:bg-dark-800 transition-colors"
                    >
                      {player}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm text-dark-400 mb-1">Prop Type</label>
            <select
              value={selectedPropType}
              onChange={(e) => setSelectedPropType(e.target.value)}
              className="w-full bg-dark-900 border border-dark-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500"
            >
              <option value="rushing_yards">Rushing Yards</option>
              <option value="receiving_yards">Receiving Yards</option>
            </select>
          </div>
        </div>
      </div>

      {/* Selected Player */}
      {selectedPlayer && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-display font-bold text-xl text-white">{selectedPlayer}</h2>
              <p className="text-dark-400 text-sm">
                {selectedPropType === 'rushing_yards' ? 'Rushing' : 'Receiving'} Yards Prop History
              </p>
            </div>
            <button
              onClick={() => setSelectedPlayer(null)}
              className="btn btn-secondary text-sm"
            >
              Clear Selection
            </button>
          </div>

          {snapshotsLoading ? (
            <div className="h-64 flex items-center justify-center text-dark-400">
              Loading snapshots...
            </div>
          ) : events.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-dark-400">
              No prop data found for this player
            </div>
          ) : (
            <div className="space-y-6">
              {events.slice(0, 5).map((event) => (
                <div key={event.event_id} className="bg-dark-900/50 rounded-lg p-4 border border-dark-700">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-white">
                      Game: {format(new Date(event.game_commence_time), 'MMM d, yyyy h:mm a')}
                    </h3>
                    <span className="text-dark-400 text-sm">
                      {event.snapshots.length} snapshots
                    </span>
                  </div>

                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart
                      data={event.snapshots.sort((a, b) => a.time - b.time)}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis
                        dataKey="hours"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        axisLine={{ stroke: '#334155' }}
                        reversed
                        label={{ value: 'Hours Before Kickoff', position: 'bottom', fill: '#94a3b8', fontSize: 11 }}
                      />
                      <YAxis
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        axisLine={{ stroke: '#334155' }}
                        domain={['auto', 'auto']}
                        label={{ value: 'Yards', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1a2235',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                        }}
                        labelFormatter={(value) => `${value}h before kickoff`}
                      />
                      <Line
                        type="stepAfter"
                        dataKey="consensus"
                        name="Consensus"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={{ fill: '#10b981', strokeWidth: 0, r: 3 }}
                      />
                      <Line
                        type="stepAfter"
                        dataKey="draftkings"
                        name="DraftKings"
                        stroke="#3b82f6"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="4 4"
                      />
                      <Line
                        type="stepAfter"
                        dataKey="fanduel"
                        name="FanDuel"
                        stroke="#8b5cf6"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="4 4"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Instructions */}
      {!selectedPlayer && (
        <div className="card text-center py-12">
          <div className="w-16 h-16 rounded-full bg-dark-800 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">🏈</span>
          </div>
          <h3 className="font-display font-semibold text-lg text-white mb-2">
            Select a Player
          </h3>
          <p className="text-dark-400 max-w-md mx-auto">
            Search for a player above to view their prop line history and see how
            lines moved leading up to each game.
          </p>
        </div>
      )}
    </div>
  )
}

