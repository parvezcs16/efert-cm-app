import { ImagePlus, Plus, Send, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { toast } from 'sonner'

import { CategoryNav } from '@/components/CategoryNav'
import { MenuItemImage } from '@/components/MenuItemTile'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Location, MenuCategory, MenuItem, MenuItemLocation } from '@/lib/types'

const IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp'

async function uploadItemImage(locationId: string, itemId: string, file: File) {
  const body = new FormData()
  body.append('file', file)
  return apiFetch<MenuItem>(`/locations/${locationId}/menu-items/${itemId}/image`, {
    method: 'PUT',
    body,
  })
}

function formatPrice(price: string): string {
  return `Rs ${Number(price).toLocaleString('en-PK', { maximumFractionDigits: 2 })}`
}

function MenuItemRow({
  locationId,
  item,
  pricing,
  onChange,
}: {
  locationId: string
  item: MenuItem
  pricing: MenuItemLocation | undefined
  onChange: (item: MenuItem) => void
}) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)

  const run = async (action: () => Promise<MenuItem>) => {
    setBusy(true)
    try {
      onChange(await action())
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (file) void run(() => uploadItemImage(locationId, item.id, file))
  }

  return (
    <li className="flex items-center gap-4 px-3 py-3 hover:bg-muted/40">
      <MenuItemImage src={item.image_url} alt={item.name} className="size-14 shrink-0 rounded-md" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{item.name}</p>
        {item.description && (
          <p className="truncate text-xs text-muted-foreground">{item.description}</p>
        )}
      </div>
      <div className="hidden w-28 shrink-0 text-right sm:block">
        {pricing ? (
          <>
            <p className="text-sm font-medium">{formatPrice(pricing.price)}</p>
            <p className="text-xs text-muted-foreground">
              {pricing.is_available ? 'Published' : 'Not published'}
            </p>
          </>
        ) : (
          <p className="text-xs text-muted-foreground">No price set</p>
        )}
      </div>
      <input
        ref={fileInput}
        type="file"
        accept={IMAGE_ACCEPT}
        className="hidden"
        onChange={handleFile}
      />
      <div className="flex shrink-0 gap-1">
        <Button
          size="sm"
          variant="outline"
          disabled={busy}
          onClick={() => fileInput.current?.click()}
          aria-label={`${item.image_url ? 'Replace' : 'Add'} image for ${item.name}`}
        >
          {busy ? <Spinner /> : <ImagePlus />}
          <span className="hidden md:inline">{item.image_url ? 'Replace' : 'Add image'}</span>
        </Button>
        {item.image_url && (
          <Button
            size="icon-sm"
            variant="ghost"
            disabled={busy}
            aria-label={`Remove image for ${item.name}`}
            onClick={() =>
              run(() =>
                apiFetch<MenuItem>(`/locations/${locationId}/menu-items/${item.id}/image`, {
                  method: 'DELETE',
                }),
              )
            }
          >
            <Trash2 />
          </Button>
        )}
      </div>
    </li>
  )
}

function AddItemDialog({
  locationId,
  category,
  open,
  onOpenChange,
  onAdded,
}: {
  locationId: string
  category: MenuCategory
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdded: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [publishNow, setPublishNow] = useState(false)
  const [image, setImage] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const preview = useMemo(() => (image ? URL.createObjectURL(image) : null), [image])

  useEffect(() => {
    if (!preview) return
    return () => URL.revokeObjectURL(preview)
  }, [preview])

  const reset = () => {
    setName('')
    setDescription('')
    setPrice('')
    setPublishNow(false)
    setImage(null)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) reset()
    onOpenChange(next)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    try {
      const item = await apiFetch<MenuItem>(
        `/locations/${locationId}/menu-categories/${category.id}/items`,
        {
          method: 'POST',
          body: JSON.stringify({
            name: name.trim(),
            description: description.trim() || null,
          }),
        },
      )
      // The item exists from here on, so a later failure still refreshes the list.
      try {
        if (price) {
          await apiFetch(`/locations/${locationId}/menu-items/${item.id}/availability`, {
            method: 'PUT',
            body: JSON.stringify({ is_available: publishNow, price }),
          })
        }
        if (image) await uploadItemImage(locationId, item.id, image)
        toast.success(`${item.name} added to ${category.name}`)
      } catch (err) {
        toast.error(`${item.name} was added, but: ${getErrorMessage(err)}`)
      }
      onAdded()
      handleOpenChange(false)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add item to {category.name}</DialogTitle>
          <DialogDescription>
            The price is internal and is never shown to employees or guests.
          </DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="item-name">Name</Label>
            <Input
              id="item-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              required
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="item-description">Description</Label>
            <Textarea
              id="item-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={2}
              placeholder="Optional"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="item-price">Price (Rs)</Label>
            <Input
              id="item-price"
              type="number"
              min="0.01"
              step="0.01"
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="Leave empty to set later"
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="item-publish"
              checked={publishNow && !!price}
              disabled={!price}
              onCheckedChange={(checked) => setPublishNow(checked === true)}
            />
            <Label htmlFor="item-publish" className="font-normal">
              Publish now so employees and guests can order it
            </Label>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="item-image">Photo</Label>
            <div className="flex items-center gap-3">
              <MenuItemImage
                src={preview}
                alt="Selected photo"
                className="size-16 shrink-0 rounded-md"
              />
              <Input
                id="item-image"
                type="file"
                accept={IMAGE_ACCEPT}
                onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving ? <Spinner /> : <Plus />}
              Add item
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function ItemsForCategory({
  locationId,
  category,
}: {
  locationId: string
  category: MenuCategory
}) {
  const [items, setItems] = useState<MenuItem[] | null>(null)
  const [pricing, setPricing] = useState<Map<string, MenuItemLocation>>(new Map())
  const [adding, setAdding] = useState(false)

  const load = () => {
    apiFetch<MenuItem[]>(`/locations/${locationId}/menu-categories/${category.id}/items`)
      .then(setItems)
      .catch((err) => toast.error(getErrorMessage(err)))
    apiFetch<MenuItemLocation[]>(`/locations/${locationId}/menu-items/availability`)
      .then((entries) => setPricing(new Map(entries.map((e) => [e.menu_item_id, e]))))
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [locationId, category.id])

  const replaceItem = (updated: MenuItem) =>
    setItems((prev) => prev?.map((i) => (i.id === updated.id ? updated : i)) ?? null)

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-primary">{category.name}</h3>
          {items !== null && (
            <p className="text-xs text-muted-foreground">
              {items.length} {items.length === 1 ? 'item' : 'items'}
            </p>
          )}
        </div>
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus />
          Add item
        </Button>
      </div>
      {items === null ? (
        <Spinner className="size-4" />
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
          No items in this category yet.
          <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
            <Plus />
            Add the first item
          </Button>
        </div>
      ) : (
        <ul className="divide-y rounded-md border bg-card">
          {items.map((item) => (
            <MenuItemRow
              key={item.id}
              locationId={locationId}
              item={item}
              pricing={pricing.get(item.id)}
              onChange={replaceItem}
            />
          ))}
        </ul>
      )}
      <AddItemDialog
        locationId={locationId}
        category={category}
        open={adding}
        onOpenChange={setAdding}
        onAdded={load}
      />
    </section>
  )
}

interface PublishGroup {
  category: MenuCategory
  items: MenuItem[]
}

function PublishMenuPanel({
  locationId,
  categories,
}: {
  locationId: string
  categories: MenuCategory[]
}) {
  const [groups, setGroups] = useState<PublishGroup[] | null>(null)
  const [pricing, setPricing] = useState<Map<string, MenuItemLocation>>(new Map())
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [publishing, setPublishing] = useState(false)

  const applyPricing = (entries: MenuItemLocation[]) => {
    setPricing(new Map(entries.map((e) => [e.menu_item_id, e])))
    setSelected(new Set(entries.filter((e) => e.is_available).map((e) => e.menu_item_id)))
  }

  useEffect(() => {
    let cancelled = false
    Promise.all([
      Promise.all(
        categories.map((category) =>
          apiFetch<MenuItem[]>(
            `/locations/${locationId}/menu-categories/${category.id}/items`,
          ).then((items) => ({ category, items })),
        ),
      ),
      apiFetch<MenuItemLocation[]>(`/locations/${locationId}/menu-items/availability`),
    ])
      .then(([loaded, entries]) => {
        if (cancelled) return
        setGroups(loaded)
        applyPricing(entries)
      })
      .catch((err) => toast.error(getErrorMessage(err)))
    return () => {
      cancelled = true
    }
  }, [locationId, categories])

  const live = useMemo(
    () => new Set([...pricing.values()].filter((e) => e.is_available).map((e) => e.menu_item_id)),
    [pricing],
  )
  const dirty = live.size !== selected.size || [...selected].some((id) => !live.has(id))

  const setMany = (ids: string[], on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev)
      for (const id of ids) {
        if (on) next.add(id)
        else next.delete(id)
      }
      return next
    })

  const publish = async () => {
    setPublishing(true)
    try {
      const entries = await apiFetch<MenuItemLocation[]>(
        `/locations/${locationId}/menu/published`,
        {
          method: 'PUT',
          body: JSON.stringify({ menu_item_ids: [...selected] }),
        },
      )
      applyPricing(entries)
      toast.success(
        `Menu published with ${selected.size} ${selected.size === 1 ? 'dish' : 'dishes'}`,
      )
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setPublishing(false)
    }
  }

  if (groups === null) return <Spinner className="size-5" />

  const nonEmptyGroups = groups.filter((g) => g.items.length > 0)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-muted/40 px-3 py-2">
        <p className="text-sm">
          <span className="font-medium">{selected.size}</span> of {pricing.size} priced dishes
          selected
          {dirty && <span className="ml-2 text-muted-foreground">· unpublished changes</span>}
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!dirty || publishing}
            onClick={() => setSelected(new Set(live))}
          >
            Discard changes
          </Button>
          <Button size="sm" disabled={!dirty || publishing} onClick={publish}>
            {publishing ? <Spinner /> : <Send />}
            Publish menu
          </Button>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Employees and guests can only order the dishes you publish. Unselected dishes stay in the
        catalog and can be published again any time.
      </p>
      {nonEmptyGroups.length === 0 ? (
        <p className="text-sm text-muted-foreground">No dishes in the catalog yet.</p>
      ) : (
        nonEmptyGroups.map(({ category, items }) => {
          const priced = items.filter((i) => pricing.has(i.id)).map((i) => i.id)
          const allOn = priced.length > 0 && priced.every((id) => selected.has(id))
          return (
            <section key={category.id} className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-primary">
                  {category.name}
                  {category.status !== 'ACTIVE' && (
                    <Badge variant="outline" className="ml-2">
                      Category hidden
                    </Badge>
                  )}
                </h3>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={priced.length === 0}
                  onClick={() => setMany(priced, !allOn)}
                >
                  {allOn ? 'Clear all' : 'Select all'}
                </Button>
              </div>
              <ul className="divide-y rounded-md border bg-card">
                {items.map((item) => {
                  const hasPrice = pricing.has(item.id)
                  const inputId = `publish-${item.id}`
                  return (
                    <li key={item.id} className="flex items-center gap-3 px-3 py-2">
                      <Checkbox
                        id={inputId}
                        checked={selected.has(item.id)}
                        disabled={!hasPrice}
                        onCheckedChange={(checked) => setMany([item.id], checked === true)}
                      />
                      <MenuItemImage
                        src={item.image_url}
                        alt={item.name}
                        className="size-10 shrink-0 rounded-md"
                      />
                      <Label htmlFor={inputId} className="min-w-0 flex-1 font-normal">
                        <span className="block truncate">{item.name}</span>
                        {!hasPrice ? (
                          <span className="text-xs text-muted-foreground">
                            Set a price before publishing
                          </span>
                        ) : (
                          item.status !== 'ACTIVE' && (
                            <span className="text-xs text-muted-foreground">
                              Item is hidden in the catalog
                            </span>
                          )
                        )}
                      </Label>
                      {live.has(item.id) && <Badge variant="secondary">Live</Badge>}
                    </li>
                  )
                })}
              </ul>
            </section>
          )
        })
      )}
    </div>
  )
}

function MenuForLocation({ locationId }: { locationId: string }) {
  const [categories, setCategories] = useState<MenuCategory[] | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [newCategory, setNewCategory] = useState('')

  const load = (select?: string) => {
    apiFetch<MenuCategory[]>(`/locations/${locationId}/menu-categories`)
      .then((loaded) => {
        setCategories(loaded)
        setSelectedId((current) => {
          const wanted = select ?? current
          return loaded.some((c) => c.id === wanted) ? wanted : (loaded[0]?.id ?? null)
        })
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [locationId])

  const addCategory = async () => {
    try {
      const created = await apiFetch<MenuCategory>(`/locations/${locationId}/menu-categories`, {
        method: 'POST',
        body: JSON.stringify({ name: newCategory, display_order: 0 }),
      })
      setNewCategory('')
      load(created.id)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const selected = categories?.find((c) => c.id === selectedId) ?? null

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
          <Tabs defaultValue="catalog">
            <TabsList>
              <TabsTrigger value="catalog">Full catalog</TabsTrigger>
              <TabsTrigger value="published">Published menu</TabsTrigger>
            </TabsList>
            <TabsContent value="published" className="pt-2">
              <PublishMenuPanel locationId={locationId} categories={categories} />
            </TabsContent>
            <TabsContent value="catalog">
              <div className="grid grid-cols-1 gap-4 border-t pt-4 lg:grid-cols-[12rem_1fr] lg:gap-6">
                <CategoryNav
                  categories={categories.map((c) => ({
                    id: c.id,
                    name: c.name,
                    note: c.status === 'ACTIVE' ? undefined : 'Hidden',
                  }))}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
                <div className="min-w-0">
                  {selected ? (
                    <ItemsForCategory
                      key={selected.id}
                      locationId={locationId}
                      category={selected}
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground">Add a category to get started.</p>
                  )}
                </div>
              </div>
            </TabsContent>
          </Tabs>
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
