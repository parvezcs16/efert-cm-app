import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import type { EmployeeRole } from '@/lib/types'

interface PendingRegistration {
  id: string
  p_no: string
  email: string
  name: string
  status: string
}

const ROLES: EmployeeRole[] = [
  'EMPLOYEE',
  'SERVER',
  'KITCHEN_OPERATOR',
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'FINANCE_ADMIN',
  'SYSTEM_ADMINISTRATOR',
]

function CreateEmployeeForm() {
  const [pNo, setPNo] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<EmployeeRole>('EMPLOYEE')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await apiFetch('/employees', {
        method: 'POST',
        body: JSON.stringify({ p_no: pNo, name, email, role }),
      })
      toast.success('Employee created — credentials emailed')
      setPNo('')
      setName('')
      setEmail('')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Create employee</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor="new_p_no">P-Number</Label>
          <Input id="new_p_no" value={pNo} onChange={(e) => setPNo(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="new_name">Name</Label>
          <Input id="new_name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="new_email">Email</Label>
          <Input id="new_email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label>Role</Label>
          <Select value={role} onValueChange={(v) => setRole(v as EmployeeRole)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => (
                <SelectItem key={r} value={r}>
                  {r}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="sm:col-span-2">
          <Button onClick={handleSubmit} disabled={submitting || !pNo || !name || !email}>
            {submitting && <Spinner />}
            Create
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function EmployeesTab() {
  const [pending, setPending] = useState<PendingRegistration[] | null>(null)

  const load = () => {
    apiFetch<PendingRegistration[]>('/auth/registrations')
      .then(setPending)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [])

  const decide = async (id: string, decision: 'approve' | 'reject') => {
    try {
      await apiFetch(`/auth/registrations/${id}/${decision}`, {
        method: 'POST',
        ...(decision === 'reject' ? { body: JSON.stringify({}) } : {}),
      })
      toast.success(`Registration ${decision}d`)
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <CreateEmployeeForm />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pending registrations</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {pending === null ? (
            <Spinner className="size-5" />
          ) : pending.length === 0 ? (
            <p className="text-sm text-muted-foreground">No pending registrations.</p>
          ) : (
            pending.map((reg) => (
              <div key={reg.id} className="flex items-center justify-between border-b pb-2 text-sm">
                <span>
                  {reg.name} ({reg.p_no}) — {reg.email}
                </span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => decide(reg.id, 'approve')}>
                    Approve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => decide(reg.id, 'reject')}>
                    Reject
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}
