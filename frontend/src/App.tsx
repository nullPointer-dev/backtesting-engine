import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { RedirectIfSignedIn, RequireAuth } from './auth/RequireAuth'
import { AppShell } from './components/AppShell'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { NotFound } from './pages/NotFound'

// App screens load on demand; the landing and sign-in pages stay in the main bundle.
const Backtests = lazy(() => import('./pages/Backtests').then((m) => ({ default: m.Backtests })))
const Builder = lazy(() => import('./pages/Builder').then((m) => ({ default: m.Builder })))
const Compare = lazy(() => import('./pages/Compare').then((m) => ({ default: m.Compare })))
const MarketData = lazy(() => import('./pages/MarketData').then((m) => ({ default: m.MarketData })))
const NewBacktest = lazy(() => import('./pages/NewBacktest').then((m) => ({ default: m.NewBacktest })))
const Overview = lazy(() => import('./pages/Overview').then((m) => ({ default: m.Overview })))
const Results = lazy(() => import('./pages/Results').then((m) => ({ default: m.Results })))
const Run = lazy(() => import('./pages/Run').then((m) => ({ default: m.Run })))
const Strategies = lazy(() => import('./pages/Strategies').then((m) => ({ default: m.Strategies })))

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfSignedIn />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/overview" element={<Overview />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/strategies/new" element={<Builder />} />
          <Route path="/strategies/:strategyId" element={<Builder key="edit" />} />
          <Route path="/backtests" element={<Backtests />} />
          <Route path="/backtests/new" element={<NewBacktest />} />
          <Route path="/backtests/:backtestId" element={<Results />} />
          <Route path="/backtests/:backtestId/run" element={<Run />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/market-data" element={<MarketData />} />
          <Route path="/dashboard" element={<Navigate to="/overview" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
