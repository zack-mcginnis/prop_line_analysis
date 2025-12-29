import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface ThesisSummary {
  thesis: string
  conclusion: string
  is_supported: boolean
  key_finding: string
  sample_size: number
  under_rate: number
  over_rate: number
  p_value: number | null
  is_significant: boolean
  recommendations: string[]
}

export interface Movement {
  id: number
  event_id: string
  player_name: string
  prop_type: string
  initial_line: number
  final_line: number
  movement_absolute: number
  movement_pct: number
  hours_before_kickoff: number
  actual_yards: number | null
  went_over: boolean | null
  went_under: boolean | null
  game_commence_time: string
}

export interface MovementSummary {
  total_movements: number
  with_results: number
  over_count: number
  under_count: number
  over_rate: number | null
  under_rate: number | null
}

export interface AnalysisResult {
  id: number
  analysis_name: string
  prop_type: string | null
  movement_threshold_pct: number | null
  movement_threshold_abs: number | null
  hours_before_threshold: number | null
  sample_size: number
  over_count: number
  under_count: number
  push_count: number
  over_rate: number
  under_rate: number
  p_value: number | null
  is_significant: boolean | null
  confidence_interval_low: number | null
  confidence_interval_high: number | null
  baseline_over_rate: number | null
  baseline_sample_size: number | null
  created_at: string
}

export interface PropSnapshot {
  id: number
  event_id: string
  player_name: string
  prop_type: string
  consensus_line: number | null
  draftkings_line: number | null
  fanduel_line: number | null
  betmgm_line: number | null
  snapshot_time: string
  game_commence_time: string
  hours_before_kickoff: number | null
  source: string
}

// API functions
export const getThesisSummary = async (): Promise<ThesisSummary> => {
  const { data } = await api.get('/analysis/thesis-summary')
  return data
}

export const getMovements = async (params?: {
  player_name?: string
  prop_type?: string
  min_movement_pct?: number
  max_hours_before?: number
  went_under?: boolean
  page?: number
  page_size?: number
}): Promise<{ items: Movement[]; total: number; page: number; page_size: number }> => {
  const { data } = await api.get('/movements/', { params })
  return data
}

export const getMovementSummary = async (params?: {
  prop_type?: string
  min_movement_pct?: number
  max_hours_before?: number
}): Promise<MovementSummary> => {
  const { data } = await api.get('/movements/summary', { params })
  return data
}

export const getAnalysisResults = async (params?: {
  prop_type?: string
  is_significant?: boolean
}): Promise<AnalysisResult[]> => {
  const { data } = await api.get('/analysis/results', { params })
  return data
}

export const getAnalysisComparison = async (propType?: string) => {
  const { data } = await api.get('/analysis/compare', { 
    params: { prop_type: propType }
  })
  return data
}

export const getPlayers = async (search?: string): Promise<{ players: string[] }> => {
  const { data } = await api.get('/props/players', { params: { search } })
  return data
}

export const getPropSnapshots = async (params?: {
  player_name?: string
  event_id?: string
  prop_type?: string
  page?: number
  page_size?: number
}): Promise<{ items: PropSnapshot[]; total: number }> => {
  const { data } = await api.get('/props/snapshots', { params })
  return data
}

export const triggerAnalysis = async () => {
  const { data } = await api.post('/analysis/run')
  return data
}

export const triggerDetection = async (params?: {
  threshold_pct?: number
  threshold_abs?: number
  hours_before?: number
}) => {
  const { data } = await api.post('/movements/detect', null, { params })
  return data
}

export const getHealthStatus = async () => {
  const { data } = await api.get('/health')
  return data
}

export default api

