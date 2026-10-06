import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { BrandLogo } from '@/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { useAuth } from '@/features/auth/AuthContext'
import { apiFetch, getErrorMessage } from '@/lib/api'
import { employeeAuthStorage } from '@/lib/auth-storage'

type Step = 'credentials' | 'otp' | 'password'

export function ActivationPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { refreshProfile } = useAuth()

  const [step, setStep] = useState<Step>('credentials')
  const [pNo, setPNo] = useState((location.state as { pNo?: string } | null)?.pNo ?? '')
  const [temporaryPassword, setTemporaryPassword] = useState('')
  const [code, setCode] = useState('')
  const [changeToken, setChangeToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleStart = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await apiFetch('/auth/activation/start', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, temporary_password: temporaryPassword }),
      })
      setStep('otp')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOtp = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await apiFetch<{ change_token: string }>('/auth/activation/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, code }),
      })
      setChangeToken(result.change_token)
      setStep('password')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleSetPassword = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      const tokens = await apiFetch<{ access_token: string; refresh_token: string }>(
        '/auth/activation/set-password',
        {
          method: 'POST',
          body: JSON.stringify({ p_no: pNo, change_token: changeToken, new_password: newPassword }),
        },
      )
      employeeAuthStorage.setTokens(tokens.access_token, tokens.refresh_token)
      await refreshProfile()
      navigate('/', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-gradient-to-br from-secondary via-background to-accent p-4">
      <BrandLogo size="lg" />
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">Activate your account</CardTitle>
          <CardDescription>
            {step === 'credentials' && 'Enter your P-Number and temporary password.'}
            {step === 'otp' && 'Enter the code sent to your email.'}
            {step === 'password' && 'Choose a new password.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {step === 'credentials' && (
            <form className="flex flex-col gap-4" onSubmit={handleStart}>
              <div className="flex flex-col gap-2">
                <Label htmlFor="p_no">P-Number</Label>
                <Input id="p_no" value={pNo} onChange={(e) => setPNo(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="temp_password">Temporary password</Label>
                <Input
                  id="temp_password"
                  type="password"
                  value={temporaryPassword}
                  onChange={(e) => setTemporaryPassword(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Send activation code
              </Button>
            </form>
          )}

          {step === 'otp' && (
            <form className="flex flex-col gap-4" onSubmit={handleVerifyOtp}>
              <div className="flex flex-col gap-2">
                <Label htmlFor="code">6-digit code</Label>
                <Input
                  id="code"
                  inputMode="numeric"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Verify code
              </Button>
            </form>
          )}

          {step === 'password' && (
            <form className="flex flex-col gap-4" onSubmit={handleSetPassword}>
              <div className="flex flex-col gap-2">
                <Label htmlFor="new_password">New password</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="confirm_password">Confirm password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Activate and sign in
              </Button>
            </form>
          )}

          <Link
            to="/login"
            className="mt-4 block text-center text-sm text-muted-foreground hover:underline"
          >
            Back to sign in
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
