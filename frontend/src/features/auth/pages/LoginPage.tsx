import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { BrandLogo, BrandStripe } from '@/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { useAuth } from '@/features/auth/AuthContext'
import { getErrorMessage } from '@/lib/api'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [pNo, setPNo] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { mustChangePassword } = await login(pNo, password)
      if (mustChangePassword) {
        navigate('/activate', { state: { pNo } })
      } else {
        navigate(from, { replace: true })
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-gradient-to-br from-secondary via-background to-accent p-4">
      <BrandLogo size="lg" />
      <Card className="w-full max-w-sm overflow-hidden">
        <BrandStripe />
        <CardHeader>
          <CardTitle className="text-xl">Sign in</CardTitle>
          <CardDescription>Use your P-Number and password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-2">
              <Label htmlFor="p_no">P-Number</Label>
              <Input
                id="p_no"
                value={pNo}
                onChange={(e) => setPNo(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={loading} className="mt-2">
              {loading && <Spinner />}
              Sign in
            </Button>
          </form>
          <div className="mt-4 flex flex-col gap-1 text-center text-sm text-muted-foreground">
            <Link to="/activate" className="hover:text-foreground hover:underline">
              Activate your account
            </Link>
            <Link to="/forgot-password" className="hover:text-foreground hover:underline">
              Forgot your password?
            </Link>
            <Link to="/register" className="hover:text-foreground hover:underline">
              Register as a new employee
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
