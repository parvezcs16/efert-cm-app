import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/theme.dart';

/// EFERT mark + app name -- mirrors frontend/src/components/BrandLogo.tsx.
class BrandLogo extends StatelessWidget {
  final double height;
  final bool showName;
  final Color? nameColor;

  const BrandLogo({
    super.key,
    this.height = 32,
    this.showName = true,
    this.nameColor,
  });

  @override
  Widget build(BuildContext context) {
    final large = height >= 48;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset('assets/images/efert_logo.png', height: height),
        if (showName) ...[
          const SizedBox(width: 8),
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'EFERT',
                style: TextStyle(
                  fontSize: large ? 24 : 16,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1,
                  color: nameColor ?? BrandColors.dark,
                ),
              ),
              Text(
                'Central Mess',
                style: TextStyle(
                  fontSize: large ? 14 : 11,
                  color: (nameColor ?? Colors.black).withValues(alpha: 0.6),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

/// Dark-green -> green -> lime strip echoing the logo's layers.
class BrandStripe extends StatelessWidget {
  final double height;

  const BrandStripe({super.key, this.height = 4});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [BrandColors.dark, BrandColors.green, BrandColors.lime],
        ),
      ),
    );
  }
}

/// Square menu photo from the API's /media path, or a neutral placeholder.
class MenuItemImage extends StatelessWidget {
  final String? imageUrl;
  final double size;
  final BorderRadius borderRadius;

  const MenuItemImage({
    super.key,
    required this.imageUrl,
    this.size = 72,
    this.borderRadius = const BorderRadius.all(Radius.circular(8)),
  });

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      width: size,
      height: size,
      color: const Color(0xFFEAF3E1),
      child: Icon(Icons.restaurant, color: BrandColors.lime, size: size * 0.4),
    );
    final url = ApiClient.mediaUrl(imageUrl);
    return ClipRRect(
      borderRadius: borderRadius,
      child: url == null
          ? placeholder
          : Image.network(
              url,
              width: size,
              height: size,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) => placeholder,
            ),
    );
  }
}
