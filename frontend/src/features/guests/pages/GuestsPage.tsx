import { QRCodeSVG } from 'qrcode.react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Guest, GuestSession, GuestType } from '@/lib/types'

interface GuestSessionCreateResponse {
  session: GuestSession
  qr_token: string
}

function RegisterGuestForm({ onRegistered }: { onRegistered: () => void }) {
  const [name, setName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [cnic, setCnic] = useState('')
  const [guestType, setGuestType] = useState<GuestType>('PRIVATE')
  const [accompanyingPersons, setAccompanyingPersons] = useState('0')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await apiFetch('/guests', {
        method: 'POST',
        body: JSON.stringify({
          name,
          company_name: companyName,
          cnic,
          guest_type: guestType,
          accompanying_persons: Number(accompanyingPersons),
        }),
      })
      toast.success('Guest registered')
      setName('')
      setCompanyName('')
      setCnic('')
      setAccompanyingPersons('0')
      onRegistered()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Register a guest</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="guest_name">Name</Label>
          <Input id="guest_name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="company_name">Company</Label>
          <Input
            id="company_name"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="cnic">CNIC</Label>
          <Input id="cnic" value={cnic} onChange={(e) => setCnic(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Guest type</Label>
          <Select value={guestType} onValueChange={(v) => setGuestType(v as GuestType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="PRIVATE">Private</SelectItem>
              <SelectItem value="OFFICIAL">Official</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="accompanying">Accompanying persons</Label>
          <Input
            id="accompanying"
            type="number"
            min={0}
            value={accompanyingPersons}
            onChange={(e) => setAccompanyingPersons(e.target.value)}
          />
        </div>
        <div className="flex items-end sm:col-span-2">
          <Button
            onClick={handleSubmit}
            disabled={submitting || !name || !companyName || !cnic}
            className="w-full sm:w-auto"
          >
            {submitting && <Spinner />}
            Register guest
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function GuestRow({ guest, onChanged }: { guest: Guest; onChanged: () => void }) {
  const [sessions, setSessions] = useState<GuestSession[] | null>(null)
  const [qr, setQr] = useState<{ token: string; sessionId: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const loadSessions = () => {
    apiFetch<GuestSession[]>(`/guests/${guest.id}/sessions`)
      .then(setSessions)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  const openSession = async () => {
    setBusy(true)
    try {
      const result = await apiFetch<GuestSessionCreateResponse>(`/guests/${guest.id}/sessions`, {
        method: 'POST',
      })
      setQr({ token: result.qr_token, sessionId: result.session.id })
      loadSessions()
      onChanged()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const closeSession = async (sessionId: string) => {
    setBusy(true)
    try {
      await apiFetch(`/guests/sessions/${sessionId}/close`, { method: 'POST' })
      loadSessions()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const reopenSession = async (sessionId: string) => {
    setBusy(true)
    try {
      await apiFetch(`/guests/sessions/${sessionId}/reopen`, { method: 'POST' })
      loadSessions()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const guestPortalUrl = qr
    ? `${window.location.origin}/guest?token=${encodeURIComponent(qr.token)}`
    : ''

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{guest.name}</p>
            <p className="text-sm text-muted-foreground">
              {guest.company_name} · {guest.guest_type}
            </p>
          </div>
          <Button size="sm" onClick={openSession} disabled={busy}>
            New session
          </Button>
        </div>

        <Button variant="ghost" size="sm" className="w-fit" onClick={loadSessions}>
          {sessions ? 'Refresh sessions' : 'Show sessions'}
        </Button>

        {sessions && (
          <div className="flex flex-col gap-2">
            {sessions.length === 0 && (
              <p className="text-sm text-muted-foreground">No sessions yet.</p>
            )}
            {sessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between text-sm">
                <span>
                  {new Date(session.opened_at).toLocaleString()}{' '}
                  <Badge variant={session.status === 'ACTIVE' ? 'success' : 'secondary'}>
                    {session.status}
                  </Badge>
                </span>
                {session.status === 'ACTIVE' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy}
                    onClick={() => closeSession(session.id)}
                  >
                    Close
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busy}
                    onClick={() => reopenSession(session.id)}
                  >
                    Reopen
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={qr !== null} onOpenChange={(open) => !open && setQr(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Scan to order</DialogTitle>
          </DialogHeader>
          {qr && (
            <div className="flex flex-col items-center gap-3">
              <QRCodeSVG value={guestPortalUrl} size={220} />
              <p className="break-all text-center text-xs text-muted-foreground">
                {guestPortalUrl}
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  )
}

export function GuestsPage() {
  const [guests, setGuests] = useState<Guest[] | null>(null)

  const loadGuests = () => {
    apiFetch<Guest[]>('/guests')
      .then(setGuests)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(loadGuests, [])

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <RegisterGuestForm onRegistered={loadGuests} />
      <h2 className="text-sm font-semibold text-muted-foreground">Your guests</h2>
      {guests === null ? (
        <div className="flex justify-center p-8">
          <Spinner className="size-6" />
        </div>
      ) : guests.length === 0 ? (
        <p className="text-sm text-muted-foreground">No guests registered yet.</p>
      ) : (
        guests.map((guest) => <GuestRow key={guest.id} guest={guest} onChanged={loadGuests} />)
      )}
    </div>
  )
}
