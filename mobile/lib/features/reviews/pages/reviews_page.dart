import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/models/location.dart';
import '../../../core/models/review.dart';

class ReviewsPage extends StatefulWidget {
  const ReviewsPage({super.key});

  @override
  State<ReviewsPage> createState() => _ReviewsPageState();
}

class _ReviewsPageState extends State<ReviewsPage> {
  List<Review>? _myReviews;

  @override
  void initState() {
    super.initState();
    _loadMyReviews();
  }

  Future<void> _loadMyReviews() async {
    try {
      final data = await ApiClient.instance.get('/reviews/me') as List;
      final reviews = data
          .map((e) => Review.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _myReviews = reviews);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final reviews = _myReviews;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _SubmitReviewForm(onSubmitted: _loadMyReviews),
        const SizedBox(height: 24),
        Text('My reviews', style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 8),
        if (reviews == null)
          const Padding(
            padding: EdgeInsets.all(32),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (reviews.isEmpty)
          const Text('No reviews yet.')
        else
          for (final review in reviews)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _StarRow(value: review.overallRating, size: 16),
                        Row(
                          children: [
                            if (review.isAnonymous) ...[
                              const Chip(label: Text('Anonymous')),
                              const SizedBox(width: 4),
                            ],
                            Chip(label: Text(review.reviewType)),
                          ],
                        ),
                      ],
                    ),
                    if (review.comment != null) ...[
                      const SizedBox(height: 4),
                      Text(review.comment!),
                    ],
                    const SizedBox(height: 4),
                    Text(
                      DateTime.parse(review.createdAt).toLocal().toString(),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
      ],
    );
  }
}

class _SubmitReviewForm extends StatefulWidget {
  final VoidCallback onSubmitted;

  const _SubmitReviewForm({required this.onSubmitted});

  @override
  State<_SubmitReviewForm> createState() => _SubmitReviewFormState();
}

class _SubmitReviewFormState extends State<_SubmitReviewForm> {
  List<Location> _locations = [];
  String? _locationId;
  List<ReviewCategory> _categories = [];
  int _overallRating = 0;
  final Map<String, int> _categoryRatings = {};
  final _commentController = TextEditingController();
  bool _isAnonymous = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _loadLocations();
  }

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _loadLocations() async {
    try {
      final data = await ApiClient.instance.get('/locations') as List;
      final all = data
          .map((e) => Location.fromJson(e as Map<String, dynamic>))
          .toList();
      final active = all.where((l) => l.status == 'ACTIVE').toList();
      if (!mounted) return;
      setState(() => _locations = active);
      if (active.isNotEmpty) _selectLocation(active.first.id);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _selectLocation(String locationId) async {
    setState(() {
      _locationId = locationId;
      _categoryRatings.clear();
    });
    try {
      final data =
          await ApiClient.instance.get(
                '/locations/$locationId/review-categories',
              )
              as List;
      final categories = data
          .map((e) => ReviewCategory.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _categories = categories);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _submit() async {
    if (_overallRating == 0) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Choose an overall rating')));
      return;
    }
    setState(() => _submitting = true);
    try {
      await ApiClient.instance.post(
        '/reviews',
        body: {
          'location_id': _locationId,
          'review_type': 'OVERALL',
          'is_anonymous': _isAnonymous,
          'overall_rating': _overallRating,
          'comment': _commentController.text.isEmpty
              ? null
              : _commentController.text,
          'category_ratings': _categoryRatings.entries
              .map((e) => {'category_id': e.key, 'rating': e.value})
              .toList(),
        },
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Thanks for your feedback')));
      setState(() {
        _overallRating = 0;
        _categoryRatings.clear();
        _commentController.clear();
      });
      widget.onSubmitted();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Leave a review',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _locationId,
              decoration: const InputDecoration(labelText: 'Location'),
              items: _locations
                  .map(
                    (l) => DropdownMenuItem(value: l.id, child: Text(l.name)),
                  )
                  .toList(),
              onChanged: (value) {
                if (value != null) _selectLocation(value);
              },
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Text('Overall'),
                const SizedBox(width: 12),
                _StarRow(
                  value: _overallRating,
                  onChanged: (v) => setState(() => _overallRating = v),
                ),
              ],
            ),
            for (final category in _categories)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(category.name),
                    _StarRow(
                      value: _categoryRatings[category.id] ?? 0,
                      size: 20,
                      onChanged: (v) =>
                          setState(() => _categoryRatings[category.id] = v),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 12),
            TextField(
              controller: _commentController,
              decoration: const InputDecoration(
                hintText: 'Tell us more (optional)',
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _isAnonymous,
              onChanged: (v) => setState(() => _isAnonymous = v ?? false),
              title: const Text('Submit anonymously'),
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Submit review'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StarRow extends StatelessWidget {
  final int value;
  final double size;
  final ValueChanged<int>? onChanged;

  const _StarRow({required this.value, this.size = 24, this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 1; i <= 5; i++)
          GestureDetector(
            onTap: onChanged == null ? null : () => onChanged!(i),
            child: Icon(
              i <= value ? Icons.star : Icons.star_border,
              size: size,
              color: Colors.amber,
            ),
          ),
      ],
    );
  }
}
