import { useQuery } from '@tanstack/react-query'
import type { ComponentType } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { API_URL } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { BacktestsIcon, MarketDataIcon, OverviewIcon, SignOutIcon, StrategiesIcon } from './icons'
import { Logo } from './Logo'

const NAV: { to: string; label: string; icon: ComponentType }[] = [
  { to: '/overview', label: 'Overview', icon: OverviewIcon },
  { to: '/backtests', label: 'Backtests', icon: BacktestsIcon },
  { to: '/strategies', label: 'Strategies', icon: StrategiesIcon },
  { to: '/market-data', label: 'Market data', icon: MarketDataIcon },
]

const apiHost = (() => {
  try {
    return new URL(API_URL).host
  } catch {
    return API_URL
  }
})()

function ApiHealth() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/health`)
      if (!response.ok) throw new Error(String(response.status))
      return true
    },
    refetchInterval: 30_000,
    retry: false,
  })
  const ok = health.isSuccess
  const label = health.isPending ? 'Checking API' : ok ? 'API healthy' : 'API unreachable'
  return (
    <div className="flex items-center gap-2" role="status">
      <span className={`size-2 rounded-full ${health.isPending ? 'bg-subtle' : ok ? 'bg-gain' : 'bg-loss'}`} />
      {label} · {apiHost}
    </div>
  )
}

export function AppShell() {
  const { user, signOut } = useAuth()

  return (
    <div className="flex min-h-screen flex-wrap bg-canvas">
      <aside className="flex max-w-full flex-[0_0_232px] flex-col gap-7 border-r border-line bg-panel px-4 py-6 max-md:flex-[1_1_100%] max-md:border-r-0 max-md:border-b">
        <div className="px-3">
          <Logo />
        </div>
        <nav aria-label="Primary" className="flex flex-col gap-1 max-md:flex-row max-md:flex-wrap">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl p-3 text-sm hover:bg-panel-2 ${
                  isActive ? 'bg-panel-2 font-semibold text-ink' : 'font-medium text-muted'
                }`
              }
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-2.5 px-3 text-[13px] text-subtle">
          <ApiHealth />
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-medium text-ink">{user?.username ?? '…'}</span>
            <button
              type="button"
              onClick={signOut}
              aria-label="Sign out"
              title="Sign out"
              className="inline-flex size-9 cursor-pointer items-center justify-center rounded-full text-subtle hover:bg-panel-2 hover:text-ink"
            >
              <SignOutIcon />
            </button>
          </div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-8 px-12 py-10 max-md:px-4 max-md:py-6">
        <Outlet />
      </main>
    </div>
  )
}
