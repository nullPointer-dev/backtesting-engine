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
