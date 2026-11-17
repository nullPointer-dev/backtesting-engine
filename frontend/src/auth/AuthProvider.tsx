import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler, unwrap, type Schemas } from '../api/client'

type User = Schemas['UserResponse']

interface AuthState {
  token: string | null
  user: User | undefined
  loadingUser: boolean
  signIn(username: string, password: string): Promise<void>
  register(username: string, password: string): Promise<void>
  signOut(): void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setTokenState] = useState<string | null>(getToken)

  const signOut = useCallback(() => {
    setToken(null)
    setTokenState(null)
    queryClient.clear()
  }, [queryClient])

  useEffect(() => {
    setUnauthorizedHandler(signOut)
    return () => setUnauthorizedHandler(null)
  }, [signOut])

  const me = useQuery({
    queryKey: ['me', token],
    queryFn: () => unwrap(api.GET('/auth/me')),
    enabled: !!token,
    staleTime: Infinity,
  })

  const signIn = useCallback(async (username: string, password: string) => {
    const { access_token } = await unwrap(api.POST('/auth/login', { body: { username, password } }))
    setToken(access_token)
    setTokenState(access_token)
  }, [])

  const register = useCallback(
    async (username: string, password: string) => {
      await unwrap(api.POST('/auth/register', { body: { username, password } }))
      await signIn(username, password)
    },
    [signIn],
  )

  const value = useMemo<AuthState>(
    () => ({ token, user: me.data, loadingUser: !!token && me.isPending, signIn, register, signOut }),
    [token, me.data, me.isPending, signIn, register, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
