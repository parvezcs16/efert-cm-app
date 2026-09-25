import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { AuditLogEntry, Location, ReconciliationReport, SalesSummary } from '@/lib/types'

function LocationReports({ locationId }: { locationId: string }) {
  const [summary, setSummary] = useState<SalesSummary | null>(null)
  const [reconciliation, setReconciliation] = useState<ReconciliationReport | null>(null)

  useEffect(() => {
    setSummary(null)
    setReconciliation(null)
    apiFetch<SalesSummary>(`/reports/locations/${locationId}/sales-summary`)
      .then(setSummary)
      .catch((err) => toast.error(getErrorMessage(err)))
    apiFetch<ReconciliationReport>(`/reports/locations/${locationId}/reconciliation`)
      .then(setReconciliation)
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [locationId])

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sales summary (last 30 days)</CardTitle>
        </CardHeader>
        <CardContent>
          {!summary ? (
            <Spinner className="size-5" />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Total orders</p>
                <p className="text-lg font-semibold">{summary.total_orders}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Revenue</p>
                <p className="text-lg font-semibold">{summary.total_revenue}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">By status</p>
                <p className="text-sm">
                  {Object.entries(summary.orders_by_status)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(', ')}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">By type</p>
                <p className="text-sm">
                  {Object.entries(summary.orders_by_type)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(', ')}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Reconciliation{' '}
            {reconciliation && (
              <Badge variant={reconciliation.mismatch_count === 0 ? 'success' : 'destructive'}>
                {reconciliation.mismatch_count} mismatch(es)
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!reconciliation ? (
            <Spinner className="size-5" />
          ) : reconciliation.lines.length === 0 ? (
            <p className="text-sm text-muted-foreground">No served items in this period.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Served / Ordered</TableHead>
                  <TableHead>Expected</TableHead>
                  <TableHead>Billed</TableHead>
                  <TableHead>Match</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reconciliation.lines.map((line) => (
                  <TableRow key={line.order_item_id}>
                    <TableCell>{line.order_number}</TableCell>
                    <TableCell>
                      {line.served_quantity} / {line.ordered_quantity}
                    </TableCell>
                    <TableCell>{line.expected_amount}</TableCell>
                    <TableCell>{line.billed_amount}</TableCell>
                    <TableCell>
                      <Badge variant={line.matches ? 'success' : 'destructive'}>
                        {line.matches ? 'OK' : 'Mismatch'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function AuditLogView() {
  const [entries, setEntries] = useState<AuditLogEntry[] | null>(null)

  useEffect(() => {
    apiFetch<AuditLogEntry[]>('/reports/audit-log')
      .then(setEntries)
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [])

  if (!entries) return <Spinner className="size-5" />

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>When</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Entity</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.slice(0, 100).map((entry) => (
          <TableRow key={entry.id}>
            <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
            <TableCell>{entry.action}</TableCell>
            <TableCell>
              {entry.entity_type} {entry.entity_id ? `#${entry.entity_id.slice(0, 8)}` : ''}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function ReportsTab() {
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')

  useEffect(() => {
    apiFetch<Location[]>('/locations')
      .then((all) => {
        setLocations(all)
        if (all.length > 0) setLocationId(all[0].id)
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <Select value={locationId} onValueChange={setLocationId}>
        <SelectTrigger className="w-64">
          <SelectValue placeholder="Location" />
        </SelectTrigger>
        <SelectContent>
          {locations.map((loc) => (
            <SelectItem key={loc.id} value={loc.id}>
              {loc.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {locationId && <LocationReports locationId={locationId} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Audit log</CardTitle>
        </CardHeader>
        <CardContent>
          <AuditLogView />
        </CardContent>
      </Card>
    </div>
  )
}
