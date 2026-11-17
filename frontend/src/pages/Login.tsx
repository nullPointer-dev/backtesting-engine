import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { Logo } from '../components/Logo'
import { ErrorNote } from '../components/ui'
import { chipClass, inputClass } from '../lib/styles'

type Mode = 'login' | 'register'

const CODE_LINES: { indent: number; delay: number; content: ReactNode; muted?: boolean }[] = [
  { indent: 0, delay: 0.2, content: '// strategy.json', muted: true },
  { indent: 0, delay: 0.5, content: <>{'{ '}<K>"long_entry"</K>: {'{'}</> },
  { indent: 1, delay: 0.8, content: <><K>"type"</K>: <S>"group"</S>, <K>"operator"</K>: <span className="text-violet">"AND"</span>,</> },
  { indent: 1, delay: 1.1, content: <><K>"children"</K>: [</> },
  { indent: 2, delay: 1.4, content: <>SMA(20) <S>crosses_above</S> SMA(50),</> },
  { indent: 2, delay: 1.7, content: <>RSI(14) <S>&gt;</S> 45</> },
  { indent: 1, delay: 2.0, content: ']' },
  { indent: 0, delay: 2.3, content: <>{'} }'}<span className="animate-[blink_1s_steps(1)_infinite] text-subtle motion-reduce:animate-none"> ▍</span></> },
]

function K({ children }: { children: ReactNode }) {
  return <span className="text-info">{children}</span>
}
function S({ children }: { children: ReactNode }) {
  return <span className="text-gain">{children}</span>
}

export function Login() {
  const { signIn, register } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<Mode>(
    new URLSearchParams(location.search).get('mode') === 'register' ? 'register' : 'login',
  )
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const login = mode === 'login'

  async function submit(event: FormEvent) {
    event.preventDefault()
    setErrors([])
    setBusy(true)
    try {
      if (login) await signIn(username.trim(), password)
      else await register(username.trim(), password)
      const from = (location.state as { from?: string } | null)?.from
      navigate(from && from !== '/login' ? from : '/overview', { replace: true })
    } catch (error) {
      setErrors(error instanceof ApiError ? error.messages : ['Something went wrong. Try again.'])
    } finally {
      setBusy(false)
    }
  }


  return (
    <div className="flex min-h-screen flex-wrap bg-canvas">
      <section
        aria-label="Product"
        className="flex min-w-0 flex-[1_1_520px] flex-col gap-10 border-r border-line bg-raised px-16 py-12 max-md:px-6"
      >
        <Link to="/" className="self-start">
          <Logo />
        </Link>
        <div className="flex max-w-[520px] flex-col gap-4">
          <h1 className="m-0 text-4xl leading-[1.15] font-semibold tracking-[-0.03em]">
            Rules as JSON.
            <br />
            Results in seconds.
          </h1>
          <p className="m-0 text-[15px] leading-relaxed text-muted">
            Chain conditions with AND / OR, pick from 24 indicators, and replay the strategy on NSE candles.
          </p>
        </div>
        <div className="mt-auto max-w-[520px] rounded-xl border border-line bg-canvas px-[22px] py-5 font-mono text-[13px] leading-[1.75]">
          <div className="mb-3 flex gap-1.5" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <span key={i} className="size-[9px] rounded-full bg-line-strong" />
            ))}
          </div>
          {CODE_LINES.map((line, i) => (
            <div
              key={i}
              className={`animate-[line-in_0.45s_ease-out_forwards] opacity-0 motion-reduce:animate-none motion-reduce:opacity-100 ${line.muted ? 'text-subtle' : ''}`}
              style={{ animationDelay: `${line.delay}s`, paddingLeft: line.indent * 20 }}
            >
              {line.content}
            </div>
          ))}
        </div>
      </section>

      <section aria-label="Account" className="flex min-w-0 flex-[1_1_460px] flex-col items-center justify-center px-16 py-12 max-md:px-6">
        <div className="flex w-full max-w-[400px] flex-col gap-7">
          <div role="group" aria-label="Mode" className="flex gap-2">
            {(
              [
                ['login', 'Sign in'],
                ['register', 'Create account'],
              ] as const
            ).map(([value, label]) => {
              const on = mode === value
              return (
                <button
                  key={value}
                  type="button"
                  aria-pressed={on}
                  onClick={() => {
                    setMode(value)
                    setErrors([])
                  }}
                  className={chipClass(on, 'flex-1')}
                >
                  {label}
                </button>
              )
            })}
          </div>

          <h2 className="m-0 text-[26px] font-semibold tracking-[-0.02em]">
            {login ? 'Welcome back' : 'Create your account'}
          </h2>

          <form className="flex flex-col gap-5" onSubmit={submit} noValidate>
            <div className="flex flex-col gap-2">
              <label htmlFor="user" className="text-[13px] font-semibold">
                Username
              </label>
              <input
                id="user"
                className={inputClass}
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={login ? undefined : 3}
                maxLength={50}
              />
            </div>
            <div className="flex flex-col gap-2">
              <label htmlFor="pw" className="text-[13px] font-semibold">
                Password
              </label>
              <input
                id="pw"
                type="password"
                className={inputClass}
                autoComplete={login ? 'current-password' : 'new-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={login ? undefined : 6}
              />
            </div>
            <ErrorNote messages={errors} />
            <button
              type="submit"
              disabled={busy || !username.trim() || !password}
              className="press h-12 cursor-pointer rounded-full bg-ink text-sm font-semibold text-canvas hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              {busy ? 'Working…' : login ? 'Sign in' : 'Create account'}
            </button>
          </form>

          {!login && (
            <p className="m-0 text-xs leading-relaxed text-subtle">
              Usernames are 3–50 characters; passwords at least 6.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
