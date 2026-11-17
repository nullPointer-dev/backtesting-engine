// React Query hooks for the backend API. Keys are grouped so mutations can invalidate them.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap, type Schemas } from './client'

export type Strategy = Schemas['StrategyResponse']
export type BacktestSummary = Schemas['BacktestSummary']
export type Backtest = Schemas['BacktestResponse']
export type BacktestStatus = Schemas['BacktestStatus']
export type Reference = Schemas['ReferenceResponse']

export const keys = {
  dashboard: ['dashboard'] as const,
  backtests: (params: object = {}) => ['backtests', params] as const,
  backtest: (id: number) => ['backtest', id] as const,
  strategies: ['strategies'] as const,
  strategy: (id: number) => ['strategy', id] as const,
  reference: ['reference'] as const,
}

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: () => unwrap(api.GET('/backtests/dashboard/summary')) })
}

export function useBacktests(params: { status?: BacktestStatus; strategy_id?: number; skip?: number; limit?: number } = {}) {
  return useQuery({
    queryKey: keys.backtests(params),
    queryFn: () => unwrap(api.GET('/backtests', { params: { query: params } })),
    placeholderData: keepPreviousData,
  })
}

export function useStrategies() {
  return useQuery({
    queryKey: keys.strategies,
    queryFn: () => unwrap(api.GET('/strategies', { params: { query: { limit: 1000 } } })),
  })
}

export function useStrategy(id: number | undefined) {
  return useQuery({
    queryKey: keys.strategy(id ?? 0),
    queryFn: () => unwrap(api.GET('/strategies/{strategy_id}', { params: { path: { strategy_id: id! } } })),
    enabled: id != null,
  })
}

/** Indicators, operators, timeframes: static per backend version. */
export function useReference() {
  return useQuery({
    queryKey: keys.reference,
    queryFn: () => unwrap(api.GET('/indicators')),
    staleTime: Infinity,
  })
}

export function useSaveStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name, strategy_json }: { id?: number; name: string; strategy_json: Record<string, unknown> }) =>
      id == null
        ? unwrap(api.POST('/strategies', { body: { name, strategy_json } }))
        : unwrap(api.PUT('/strategies/{strategy_id}', { params: { path: { strategy_id: id } }, body: { name, strategy_json } })),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: keys.strategies })
      queryClient.setQueryData(keys.strategy(saved.strategy_id), saved)
      queryClient.invalidateQueries({ queryKey: keys.dashboard })
    },
  })
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/strategies/{strategy_id}', { params: { path: { strategy_id: id } } })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.strategies })
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
      queryClient.invalidateQueries({ queryKey: keys.dashboard })
    },
  })
}

// ---------------------------------------------------------------- backtests and market data

export type Trade = Schemas['TradeResponse']
export type SymbolInfo = Schemas['SymbolInfo']
export type BacktestCreate = Schemas['BacktestCreate']
export type StatusResponse = Schemas['BacktestStatusResponse']

const ACTIVE: BacktestStatus[] = ['PENDING', 'RUNNING']

export function useSymbols() {
  return useQuery({
    queryKey: ['symbols'],
    queryFn: () => unwrap(api.GET('/market-data/symbols')),
    staleTime: 5 * 60_000,
  })
}

export function useBacktest(id: number) {
  return useQuery({
    queryKey: keys.backtest(id),
    queryFn: () => unwrap(api.GET('/backtests/{backtest_id}', { params: { path: { backtest_id: id } } })),
  })
}

/** Polls twice a second while the backtest is queued or running. */
export function useBacktestStatus(id: number) {
  return useQuery({
    queryKey: ['backtest-status', id],
    queryFn: () => unwrap(api.GET('/backtests/{backtest_id}/status', { params: { path: { backtest_id: id } } })),
    refetchInterval: (query) => (query.state.data && !ACTIVE.includes(query.state.data.status) ? false : 500),
    staleTime: 0,
  })
}

export function useTrades(id: number, enabled = true) {
  return useQuery({
    queryKey: ['trades', id],
    queryFn: () =>
      unwrap(api.GET('/backtests/{backtest_id}/trades', { params: { path: { backtest_id: id }, query: { limit: 5000 } } })),
    enabled,
  })
}

export function useHistory(symbol: string | undefined, timeframe: string | undefined, start?: string, end?: string) {
  return useQuery({
    queryKey: ['history', symbol, timeframe, start, end],
    queryFn: () =>
      unwrap(
        api.GET('/market-data/{symbol}/history', {
          params: {
            path: { symbol: symbol! },
            query: { timeframe: timeframe as Schemas['TimeFrame'], start_date: start, end_date: end, limit: 10000 },
          },
        }),
      ),
    enabled: !!symbol && !!timeframe,
    staleTime: 5 * 60_000,
  })
}

export function useReturnsBreakdown(id: number, enabled = true) {
  return useQuery({
    queryKey: ['returns', id],
    queryFn: () => unwrap(api.GET('/backtests/{backtest_id}/returns-breakdown', { params: { path: { backtest_id: id } } })),
    enabled,
  })
}

function useInvalidateBacktests() {
  const queryClient = useQueryClient()
  return (id?: number) => {
    queryClient.invalidateQueries({ queryKey: ['backtests'] })
    queryClient.invalidateQueries({ queryKey: keys.dashboard })
    if (id != null) {
      queryClient.invalidateQueries({ queryKey: keys.backtest(id) })
      queryClient.invalidateQueries({ queryKey: ['backtest-status', id] })
      queryClient.invalidateQueries({ queryKey: ['trades', id] })
      queryClient.invalidateQueries({ queryKey: ['returns', id] })
    }
  }
}

export function useCreateBacktest() {
  const invalidate = useInvalidateBacktests()
  return useMutation({
    mutationFn: (body: BacktestCreate) => unwrap(api.POST('/backtests', { body })),
    onSuccess: () => invalidate(),
  })
}

export function useRunBacktest() {
  const invalidate = useInvalidateBacktests()
  return useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/backtests/{backtest_id}/run', { params: { path: { backtest_id: id } } })),
    onSuccess: (_, id) => invalidate(id),
  })
}

export function useCancelBacktest() {
  const invalidate = useInvalidateBacktests()
  return useMutation({
    mutationFn: (id: number) => unwrap(api.POST('/backtests/{backtest_id}/cancel', { params: { path: { backtest_id: id } } })),
    onSuccess: (_, id) => invalidate(id),
  })
}

export function useDeleteBacktest() {
  const invalidate = useInvalidateBacktests()
  return useMutation({
    mutationFn: (id: number) => unwrap(api.DELETE('/backtests/{backtest_id}', { params: { path: { backtest_id: id } } })),
    onSuccess: () => invalidate(),
  })
}
