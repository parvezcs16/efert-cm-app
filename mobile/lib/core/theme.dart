import 'package:flutter/material.dart';

/// EFERT brand greens, sampled from the logo (assets/images/efert_logo.png)
/// -- the same palette as frontend/src/index.css.
class BrandColors {
  BrandColors._();

  static const dark = Color(0xFF006937);
  static const green = Color(0xFF00A651);
  static const lime = Color(0xFF7AB02C);
  static const limeLight = Color(0xFFC2D887);
  static const background = Color(0xFFF6F9F4);
}

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: BrandColors.dark,
    primary: BrandColors.dark,
    secondary: BrandColors.green,
    tertiary: BrandColors.lime,
    surface: Colors.white,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: BrandColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: BrandColors.dark,
      foregroundColor: Colors.white,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFFDBE5D8)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: BrandColors.dark,
        foregroundColor: Colors.white,
      ),
    ),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
      focusedBorder: OutlineInputBorder(
        borderSide: BorderSide(color: BrandColors.green, width: 2),
      ),
    ),
    drawerTheme: const DrawerThemeData(backgroundColor: Colors.white),
  );
}
