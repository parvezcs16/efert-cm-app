import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
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
import type { Employee, KitchenStation, Location } from '@/lib/types'

// Mirrors MANAGER_ELIGIBLE_ROLES in
// backend/app/services/locations/location_service.py.
const MANAGER_ELIGIBLE_ROLES = ['LOCATION_MANAGER', 'SYSTEM_MANAGER', 'SYSTEM_ADMINISTRATOR']

function CreateLocationForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await apiFetch('/locations', { method: 'POST', body: JSON.stringify({ name, code }) })
      toast.success('Location created')
      setName('')
      setCode('')
      onCreated()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Create location</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="loc_name">Name</Label>
          <Input id="loc_name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="loc_code">Code</Label>
          <Input id="loc_code" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <Button onClick={handleSubmit} disabled={submitting || !name || !code}>
          {submitting && <Spinner />}
          Create
        </Button>
      </CardContent>
    </Card>
  )
}

function LocationCard({
  location,
  eligibleManagers,
}: {
  location: Location
  eligibleManagers: Employee[]
}) {
  const [stations, setStations] = useState<KitchenStation[] | null>(null)
  const [newStation, setNewStation] = useState('')
  const [managerId, setManagerId] = useState('')
  const [assigning, setAssigning] = useState(false)

  const loadStations = () => {
    apiFetch<KitchenStation[]>(`/locations/${location.id}/kitchen-stations`)
      .then(setStations)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(loadStations, [location.id])

  const addStation = async () => {
    try {
      await apiFetch(`/locations/${location.id}/kitchen-stations`, {
        method: 'POST',
        body: JSON.stringify({ name: newStation }),
      })
      setNewStation('')
      loadStations()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const assignManager = async () => {
    setAssigning(true)
    try {
      await apiFetch(`/locations/${location.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ manager_id: managerId }),
      })
      toast.success('Manager assigned')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setAssigning(false)
    }
  }

  const currentManager = eligibleManagers.find((e) => e.id === location.manager_id)

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-base">
          {location.name} <span className="text-muted-foreground">({location.code})</span>
        </CardTitle>
        <Badge>{location.status}</Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-2">
            <Label>
              Manager
              {currentManager && (
                <span className="ml-2 font-normal text-muted-foreground">
                  currently {currentManager.name}
                </span>
              )}
            </Label>
            <Select value={managerId} onValueChange={setManagerId}>
              <SelectTrigger className="w-64">
                <SelectValue placeholder="Choose an eligible employee" />
              </SelectTrigger>
              <SelectContent>
                {eligibleManagers.map((emp) => (
                  <SelectItem key={emp.id} value={emp.id}>
                    {emp.name} ({emp.p_no}) — {emp.role}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button size="sm" onClick={assignManager} disabled={!managerId || assigning}>
            {assigning && <Spinner />}
            Assign
          </Button>
        </div>

        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">Kitchen stations</p>
          {stations === null ? (
            <Spinner className="size-4" />
          ) : (
            <ul className="text-sm text-muted-foreground">
              {stations.map((s) => (
                <li key={s.id}>{s.name}</li>
              ))}
            </ul>
          )}
          <div className="flex items-end gap-2">
            <Input
              placeholder="Station name"
              value={newStation}
              onChange={(e) => setNewStation(e.target.value)}
            />
            <Button size="sm" onClick={addStation} disabled={!newStation}>
              Add
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function LocationsTab() {
  const [locations, setLocations] = useState<Location[] | null>(null)
  const [eligibleManagers, setEligibleManagers] = useState<Employee[]>([])

  const load = () => {
    apiFetch<Location[]>('/locations')
      .then(setLocations)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [])

  useEffect(() => {
    const params = new URLSearchParams()
    MANAGER_ELIGIBLE_ROLES.forEach((role) => params.append('role', role))
    apiFetch<Employee[]>(`/employees?${params.toString()}`)
      .then(setEligibleManagers)
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <CreateLocationForm onCreated={load} />
      {locations === null ? (
        <Spinner className="size-5" />
      ) : (
        locations.map((loc) => (
          <LocationCard key={loc.id} location={loc} eligibleManagers={eligibleManagers} />
        ))
      )}
    </div>
  )
}
