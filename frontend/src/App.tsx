import { Navigate, Route, Routes } from 'react-router-dom'
import { RedirectIfSignedIn, RequireAuth } from './auth/RequireAuth'
import { AppShell } from './components/AppShell'
import { Builder } from './pages/Builder'
import { Login } from './pages/Login'
import { Overview } from './pages/Overview'
import { Strategies } from './pages/Strategies'
import { NotFound } from './pages/NotFound'
import { Placeholder } from './pages/Placeholder'

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfSignedIn />}>
        <Route path="/" element={<Placeholder title="Landing" />} />
        <Route path="/login" element={<Login />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route path="/overview" element={<Overview />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/strategies/new" element={<Builder />} />
          <Route path="/strategies/:strategyId" element={<Builder key="edit" />} />
          <Route path="/backtests" element={<Placeholder title="Backtests" />} />
          <Route path="/backtests/new" element={<Placeholder title="New backtest" />} />
          <Route path="/backtests/:backtestId" element={<Placeholder title="Backtest results" />} />
          <Route path="/backtests/:backtestId/run" element={<Placeholder title="Run" />} />
          <Route path="/compare" element={<Placeholder title="Compare backtests" />} />
          <Route path="/market-data" element={<Placeholder title="Market data" />} />
          <Route path="/dashboard" element={<Navigate to="/overview" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
