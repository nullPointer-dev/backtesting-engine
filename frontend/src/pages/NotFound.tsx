import { ButtonLink } from '../components/ui'

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <p className="m-0 text-sm text-subtle">404</p>
      <h1 className="m-0 text-2xl font-semibold">Nothing lives at this address.</h1>
      <ButtonLink to="/">Go home</ButtonLink>
    </div>
  )
}
