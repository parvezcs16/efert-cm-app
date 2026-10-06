import { BellRing, CheckCircle2, Clock, QrCode, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { BrandLogo, BrandStripe } from '@/components/BrandLogo'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'

export type GuestEndReason = 'closed' | 'expired' | 'missing'

const CONTENT: Record<GuestEndReason, { icon: typeof Clock; title: string; body: string }> = {
  closed: {
    icon: Clock,
    title: 'Your session has ended',
    body:
      "We're sorry — your session with EFERT Central Mess has ended. " +
      "If you'd like to order anything else, tap below and we'll let your host know.",
  },
  expired: {
    icon: QrCode,
    title: 'This QR code is no longer valid',
    body:
      "We're sorry — this QR code has expired and can't be used to order anymore. " +
      'Please contact your host for a new one.',
  },
  missing: {
    icon: QrCode,
    title: 'Scan your QR code to begin',
    body: 'Please scan the guest QR code shared by your host to start ordering.',
  },
}

// While waiting on the host, how often to check whether they reopened it.
const REOPEN_CHECK_MS = 15_000

type RequestState = 'idle' | 'sending' | 'sent'

interface GuestSessionEndedProps {
  reason: GuestEndReason
  /** The raw QR token; still valid for a closed session, so it can be used
   * to ask the host to reopen and to notice when they do. */
  qrToken?: string | null
  /** Called with a fresh access token once the host reopens the session. */
  onResumed?: (accessToken: string) => void
}

async function postGuest(path: string, token: string): Promise<Response> {
  return fetch(`/api/v1/guest${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  })
}

/** Friendly, branded dead-end screen for the guest portal. For a closed
 * session it also lets the guest ask their host to reopen it, and resumes
 * the portal automatically once the host does. */
export function GuestSessionEnded({ reason, qrToken, onResumed }: GuestSessionEndedProps) {
  const { icon: Icon, title, body } = CONTENT[reason]
  const canRequest = reason === 'closed' && !!qrToken
  const [requestState, setRequestState] = useState<RequestState>('idle')

  const requestHost = async () => {
    if (!qrToken) return
    setRequestState('sending')
    try {
      const res = await postGuest('/session/reopen-request', qrToken)
      // 429 means the host was already notified recently -- same outcome.
      if (res.ok || res.status === 429) {
        setRequestState('sent')
        return
      }
      const err = await res.json().catch(() => null)
      toast.error(err?.message ?? 'Could not reach your host. Please try again.')
      setRequestState('idle')
    } catch {
      toast.error('Unable to reach Central Mess. Please check your connection and try again.')
      setRequestState('idle')
    }
  }

  useEffect(() => {
    if (!canRequest || !qrToken || !onResumed) return
    const check = async () => {
      try {
        const res = await postGuest('/auth', qrToken)
        if (!res.ok) return
        const data: { access_token: string; session: { status: string } } = await res.json()
        if (data.session.status === 'ACTIVE') {
          toast.success('Your host reopened your session. Welcome back!')
          onResumed(data.access_token)
        }
      } catch {
        // Transient; try again on the next tick.
      }
    }
    const timer = window.setInterval(check, REOPEN_CHECK_MS)
    return () => window.clearInterval(timer)
  }, [canRequest, qrToken, onResumed])

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 bg-gradient-to-br from-secondary via-background to-accent p-4">
      <BrandLogo size="lg" />
      <Card className="w-full max-w-md overflow-hidden">
        <BrandStripe />
        <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-accent text-primary">
            <Icon className="size-7" />
          </div>
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
          {canRequest && requestState !== 'sent' && (
            <Button
              className="mt-2 w-full sm:w-auto"
              disabled={requestState === 'sending'}
              onClick={() => void requestHost()}
            >
              {requestState === 'sending' ? <Spinner /> : <BellRing />}
              Request host to order again
            </Button>
          )}
          {canRequest && requestState === 'sent' && (
            <div className="mt-2 flex flex-col items-center gap-1 rounded-lg border border-primary/20 bg-accent px-4 py-3 text-sm">
              <span className="flex items-center gap-2 font-medium text-primary">
                <CheckCircle2 className="size-4" />
                Your host has been notified
              </span>
              <span className="text-muted-foreground">
                This page will continue automatically once they reopen your session.
              </span>
            </div>
          )}
          {reason !== 'missing' && (
            <div className="mt-2 flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm text-secondary-foreground">
              <UserRound className="size-4" />
              Thank you for dining with us.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
