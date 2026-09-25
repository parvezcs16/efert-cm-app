class ReviewCategory {
  final String id;
  final String? locationId;
  final String name;
  final bool enabled;
  final bool isManagerDefined;

  ReviewCategory({
    required this.id,
    required this.locationId,
    required this.name,
    required this.enabled,
    required this.isManagerDefined,
  });

  factory ReviewCategory.fromJson(Map<String, dynamic> json) => ReviewCategory(
    id: json['id'] as String,
    locationId: json['location_id'] as String?,
    name: json['name'] as String,
    enabled: json['enabled'] as bool,
    isManagerDefined: json['is_manager_defined'] as bool,
  );
}

class ReviewCategoryRating {
  final String categoryId;
  final int rating;

  ReviewCategoryRating({required this.categoryId, required this.rating});

  factory ReviewCategoryRating.fromJson(Map<String, dynamic> json) =>
      ReviewCategoryRating(
        categoryId: json['category_id'] as String,
        rating: json['rating'] as int,
      );

  Map<String, dynamic> toJson() => {
    'category_id': categoryId,
    'rating': rating,
  };
}

class Review {
  final String id;
  final String locationId;
  final String? employeeId;
  final bool isAnonymous;
  final String reviewType;
  final String? orderId;
  final int overallRating;
  final String? comment;
  final String createdAt;
  final List<ReviewCategoryRating> categoryRatings;

  Review({
    required this.id,
    required this.locationId,
    required this.employeeId,
    required this.isAnonymous,
    required this.reviewType,
    required this.orderId,
    required this.overallRating,
    required this.comment,
    required this.createdAt,
    required this.categoryRatings,
  });

  factory Review.fromJson(Map<String, dynamic> json) => Review(
    id: json['id'] as String,
    locationId: json['location_id'] as String,
    employeeId: json['employee_id'] as String?,
    isAnonymous: json['is_anonymous'] as bool,
    reviewType: json['review_type'] as String,
    orderId: json['order_id'] as String?,
    overallRating: json['overall_rating'] as int,
    comment: json['comment'] as String?,
    createdAt: json['created_at'] as String,
    categoryRatings: (json['category_ratings'] as List)
        .map((e) => ReviewCategoryRating.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}
