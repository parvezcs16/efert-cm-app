import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Location, MenuCategory, MenuItem } from '@/lib/types'

function ItemsForCategory({ locationId, category }: { locationId: string; category: MenuCategory }) {
  const [items, setItems] = useState<MenuItem[] | null>(null)
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')

  const load = () => {
    apiFetch<MenuItem[]>(`/locations/${locationId}/menu-categories/${category.id}/items`)
      .then(setItems)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [locationId, category.id])

  const addItem = async () => {
    try {
      const item = await apiFetch<MenuItem>(
        `/locations/${locationId}/menu-categories/${category.id}/items`,
        { method: 'POST', body: JSON.stringify({ name, description: null }) },
      )
      if (price) {
        await apiFetch(`/locations/${locationId}/menu-items/${item.id}/availability`, {
          method: 'PUT',
          body: JSON.stringify({ is_available: true, price }),
        })
      }
      setName('')
      setPrice('')
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <div className="flex flex-col gap-2 border-t pt-2">
      <p className="text-sm font-medium">{category.name}</p>
      {items === null ? (
        <Spinner className="size-4" />
      ) : (
        <ul className="text-sm text-muted-foreground">
          {items.map((item) => (
            <li key={item.id}>{item.name}</li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <Input placeholder="Item name" value={name} onChange={(e) => setName(e.target.value)} />
        <Input
          placeholder="Price"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className="w-24"
        />
        <Button size="sm" onClick={addItem} disabled={!name}>
          Add item
        </Button>
      </div>
    </div>
  )
}

function MenuForLocation({ locationId }: { locationId: string }) {
  const [categories, setCategories] = useState<MenuCategory[] | null>(null)
  const [newCategory, setNewCategory] = useState('')

  const load = () => {
    apiFetch<MenuCategory[]>(`/locations/${locationId}/menu-categories`)
      .then(setCategories)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [locationId])

  const addCategory = async () => {
    try {
      await apiFetch(`/locations/${locationId}/menu-categories`, {
        method: 'POST',
        body: JSON.stringify({ name: newCategory, display_order: 0 }),
      })
      setNewCategory('')
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Menu</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <Input
            placeholder="New category"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
          />
          <Button size="sm" onClick={addCategory} disabled={!newCategory}>
            Add category
          </Button>
        </div>
        {categories === null ? (
          <Spinner className="size-5" />
        ) : (
          categories.map((cat) => (
            <ItemsForCategory key={cat.id} locationId={locationId} category={cat} />
          ))
        )}
      </CardContent>
    </Card>
  )
}

export function MenuTab() {
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
              {loc.name} <Badge variant="outline">{loc.code}</Badge>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {locationId && <MenuForLocation locationId={locationId} />}
    </div>
  )
}
