import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { BrandLogo } from '@/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'

type Step = 'request' | 'otp' | 'password' | 'done'

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('request')
  const [pNo, setPNo] = useState('')
  const [code, setCode] = useState('')
  const [changeToken, setChangeToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRequest = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await apiFetch('/auth/password/forgot', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo }),
      })
      setStep('otp')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await apiFetch<{ change_token: string }>(
        '/auth/password/reset/verify-otp',
        { method: 'POST', body: JSON.stringify({ p_no: pNo, code }) },
      )
      setChangeToken(result.change_token)
      setStep('password')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await apiFetch('/auth/password/reset', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, change_token: changeToken, new_password: newPassword }),
      })
      setStep('done')
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
          <CardTitle className="text-xl">Reset your password</CardTitle>
          <CardDescription>
            {step === 'request' && 'Enter your P-Number to receive a reset code.'}
            {step === 'otp' && 'Enter the code sent to your email.'}
            {step === 'password' && 'Choose a new password.'}
            {step === 'done' && 'Your password has been reset.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {step === 'request' && (
            <form className="flex flex-col gap-4" onSubmit={handleRequest}>
              <div className="flex flex-col gap-2">
                <Label htmlFor="p_no">P-Number</Label>
                <Input id="p_no" value={pNo} onChange={(e) => setPNo(e.target.value)} required />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Send reset code
              </Button>
            </form>
          )}

          {step === 'otp' && (
            <form className="flex flex-col gap-4" onSubmit={handleVerify}>
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
            <form className="flex flex-col gap-4" onSubmit={handleReset}>
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
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Reset password
              </Button>
            </form>
          )}

          {step === 'done' && (
            <Button className="w-full" onClick={() => navigate('/login')}>
              Back to sign in
            </Button>
          )}

          {step !== 'done' && (
            <Link
              to="/login"
              className="mt-4 block text-center text-sm text-muted-foreground hover:underline"
            >
              Back to sign in
            </Link>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
