import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { BrandLogo } from '@/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'

export function RegisterPage() {
  const [pNo, setPNo] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, name, email }),
      })
      setSubmitted(true)
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
          <CardTitle className="text-xl">Register</CardTitle>
          <CardDescription>Use your P-Number and company email.</CardDescription>
        </CardHeader>
        <CardContent>
          {submitted ? (
            <div className="flex flex-col gap-4 text-sm">
              <p>
                Your registration has been submitted and is pending admin approval. You'll
                receive an email with activation instructions once approved.
              </p>
              <Link to="/login" className="text-center text-primary hover:underline">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
              <div className="flex flex-col gap-2">
                <Label htmlFor="p_no">P-Number</Label>
                <Input id="p_no" value={pNo} onChange={(e) => setPNo(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Full name</Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="email">Company email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={loading} className="mt-2">
                {loading && <Spinner />}
                Submit registration
              </Button>
              <Link to="/login" className="text-center text-sm text-muted-foreground hover:underline">
                Back to sign in
              </Link>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
