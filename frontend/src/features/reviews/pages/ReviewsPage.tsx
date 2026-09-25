import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { StarRating } from '@/components/ui/star-rating'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Location, Review, ReviewCategory } from '@/lib/types'

function SubmitReviewForm({ onSubmitted }: { onSubmitted: () => void }) {
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')
  const [categories, setCategories] = useState<ReviewCategory[]>([])
  const [overallRating, setOverallRating] = useState(0)
  const [categoryRatings, setCategoryRatings] = useState<Record<string, number>>({})
  const [comment, setComment] = useState('')
  const [isAnonymous, setIsAnonymous] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    apiFetch<Location[]>('/locations')
      .then((all) => {
        const active = all.filter((l) => l.status === 'ACTIVE')
        setLocations(active)
        if (active.length > 0) setLocationId(active[0].id)
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [])

  useEffect(() => {
    if (!locationId) return
    apiFetch<ReviewCategory[]>(`/locations/${locationId}/review-categories`)
      .then(setCategories)
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [locationId])

  const handleSubmit = async () => {
    if (overallRating === 0) {
      toast.error('Choose an overall rating')
      return
    }
    setSubmitting(true)
    try {
      await apiFetch('/reviews', {
        method: 'POST',
        body: JSON.stringify({
          location_id: locationId,
          review_type: 'OVERALL',
          is_anonymous: isAnonymous,
          overall_rating: overallRating,
          comment: comment || null,
          category_ratings: Object.entries(categoryRatings).map(([category_id, rating]) => ({
            category_id,
            rating,
          })),
        }),
      })
      toast.success('Thanks for your feedback')
      setOverallRating(0)
      setCategoryRatings({})
      setComment('')
      onSubmitted()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Leave a review</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Select value={locationId} onValueChange={setLocationId}>
          <SelectTrigger>
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

        <div className="flex items-center gap-3">
          <span className="text-sm font-medium">Overall</span>
          <StarRating value={overallRating} onChange={setOverallRating} />
        </div>

        {categories.map((category) => (
          <div key={category.id} className="flex items-center justify-between gap-3">
            <span className="text-sm">{category.name}</span>
            <StarRating
              value={categoryRatings[category.id] ?? 0}
              onChange={(v) => setCategoryRatings((prev) => ({ ...prev, [category.id]: v }))}
              size={16}
            />
          </div>
        ))}

        <Textarea
          placeholder="Tell us more (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />

        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={isAnonymous} onCheckedChange={(v) => setIsAnonymous(v === true)} />
          Submit anonymously
        </label>

        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting && <Spinner />}
          Submit review
        </Button>
      </CardContent>
    </Card>
  )
}

function ReviewList({ reviews }: { reviews: Review[] | null }) {
  if (reviews === null) {
    return (
      <div className="flex justify-center p-8">
        <Spinner className="size-6" />
      </div>
    )
  }
  if (reviews.length === 0) {
    return <p className="text-sm text-muted-foreground">No reviews yet.</p>
  }
  return (
    <div className="flex flex-col gap-3">
      {reviews.map((review) => (
        <Card key={review.id}>
          <CardContent className="flex flex-col gap-1 p-4">
            <div className="flex items-center justify-between">
              <StarRating value={review.overall_rating} onChange={() => {}} size={16} />
              <div className="flex gap-2">
                {review.is_anonymous && <Badge variant="outline">Anonymous</Badge>}
                <Badge variant="secondary">{review.review_type}</Badge>
              </div>
            </div>
            {review.comment && <p className="text-sm">{review.comment}</p>}
            <p className="text-xs text-muted-foreground">
              {new Date(review.created_at).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function ReviewsPage() {
  const [myReviews, setMyReviews] = useState<Review[] | null>(null)

  const loadMyReviews = () => {
    apiFetch<Review[]>('/reviews/me')
      .then(setMyReviews)
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(loadMyReviews, [])

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <SubmitReviewForm onSubmitted={loadMyReviews} />
      <Tabs defaultValue="mine">
        <TabsList>
          <TabsTrigger value="mine">My reviews</TabsTrigger>
        </TabsList>
        <TabsContent value="mine">
          <ReviewList reviews={myReviews} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
