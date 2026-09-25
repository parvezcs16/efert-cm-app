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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAuth } from '@/features/auth/AuthContext'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Statement, StatementFrequency } from '@/lib/types'

const TABS: { value: string; label: string; path: string }[] = [
  { value: 'personal', label: 'Personal', path: '/billing/me/personal' },
  { value: 'private-guests', label: 'Private guests', path: '/billing/me/private-guests' },
  { value: 'consolidated', label: 'Consolidated', path: '/billing/me/consolidated' },
]

const FREQUENCIES: StatementFrequency[] = ['DAILY', 'WEEKLY', 'BIWEEKLY', 'MONTHLY']

function StatementView({ path }: { path: string }) {
  const [statement, setStatement] = useState<Statement | null>(null)

  useEffect(() => {
    setStatement(null)
    apiFetch<Statement>(path)
      .then(setStatement)
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [path])

  if (!statement) {
    return (
      <div className="flex justify-center p-8">
        <Spinner className="size-6" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-3 text-center">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Charges</p>
            <p className="text-lg font-semibold">{statement.total_debit}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Credits</p>
            <p className="text-lg font-semibold">{statement.total_credit}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Net balance</p>
            <p className="text-lg font-semibold">{statement.net_balance}</p>
          </CardContent>
        </Card>
      </div>

      {statement.entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No activity yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {statement.entries.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{new Date(entry.created_at).toLocaleDateString()}</TableCell>
                <TableCell>{entry.reason}</TableCell>
                <TableCell>
                  <Badge variant={entry.entry_type === 'DEBIT' ? 'secondary' : 'success'}>
                    {entry.entry_type}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{entry.amount}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}

export function BillingPage() {
  const { employee, refreshProfile } = useAuth()
  const [updatingFrequency, setUpdatingFrequency] = useState(false)

  const handleFrequencyChange = async (frequency: string) => {
    setUpdatingFrequency(true)
    try {
      await apiFetch('/employees/me/statement-frequency', {
        method: 'PATCH',
        body: JSON.stringify({ frequency }),
      })
      await refreshProfile()
      toast.success('Statement frequency updated')
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setUpdatingFrequency(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Statement preferences</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Email me a statement</span>
          <Select
            value={employee?.statement_frequency}
            onValueChange={handleFrequencyChange}
            disabled={updatingFrequency}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FREQUENCIES.map((f) => (
                <SelectItem key={f} value={f}>
                  {f}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Tabs defaultValue="personal">
        <TabsList>
          {TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {TABS.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <StatementView path={tab.path} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
