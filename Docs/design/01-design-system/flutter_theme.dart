// iBackHome design tokens for the Flutter Android app (supervisor and contractor).
// Generated from 01-design-system/tokens.json. Fonts: bundle Inter (400/500/600/700) and
// JetBrains Mono (400/500) from 05-assets/fonts and declare them in pubspec.yaml.
// Rules: 48dp touch targets; body text 15/22 minimum; status colours only in chips and alerts.
import 'package:flutter/material.dart';

class IbhColors {
  IbhColors._();
  static const navy900 = Color(0xFF131F39); // Primary: buttons, header and price blocks, active states
  static const navy800 = Color(0xFF1E2B4A); // Primary hover / pressed
  static const navy700 = Color(0xFF2A3753); // Raised surface on navy (inputs and chips on navy blocks)
  static const navy200 = Color(0xFFC9D3E3); // Text and lines on navy
  static const ink = Color(0xFF0B1324); // Headings and strong text
  static const slate = Color(0xFF3A4354); // Body text
  static const muted = Color(0xFF5F6878); // Secondary text (4.5:1 on white and mist)
  static const white = Color(0xFFFFFFFF); // Page and card background
  static const mist = Color(0xFFF4F8FB); // Secondary surface: secondary buttons, inputs, panels
  static const canvas = Color(0xFFF1F3F5); // App background behind cards; board background
  static const line = Color(0xFFE4E8EE); // Hairline borders and dividers
  static const lineStrong = Color(0xFF7E889A); // Input borders, dashed placeholders (3:1 non-text contrast)
  static const frame = Color(0xFFD5DBE3); // Card outline, secondary button border
  static const accent = Color(0xFF2F5FC4); // Links, focus ring, selected states only
  static const accentHover = Color(0xFF1F4699); // Link hover
  static const accentTint = Color(0xFFE8EFFC); // Selected row / info chip background
  static const rowHighlight = Color(0xFFF7FAFF); // Hovered or selected table row
  static const focusOnDark = Color(0xFF7FA2E8); // Focus ring on navy surfaces
  static const escrowBar = Color(0xFF8C97AD); // "In escrow" segment of the spend bar
  static const placeholder = Color(0xFFE6ECF3); // Photo / media placeholder blocks
  static const camera = Color(0xFF1B2436); // Camera preview surface

  // Status (chips and alerts only)
  static const okBg = Color(0xFFE7F4EC);
  static const okFg = Color(0xFF1E6B45);
  static const warnBg = Color(0xFFFDF1D8);
  static const warnFg = Color(0xFF8A5300);
  static const badBg = Color(0xFFFDECEA);
  static const badFg = Color(0xFFB42318);
  static const neutralBg = Color(0xFFEEF1F5);
  static const neutralFg = Color(0xFF4A5363);
  static const infoBg = Color(0xFFE8EFFC);
  static const infoFg = Color(0xFF2552B0);

  // Supplementary values found on approved boards (confirm or replace)
  static const placeholderBorder = Color(0xFFC2CAD5); // Dashed border of "coming soon" and empty placeholders
  static const mapLand = Color(0xFFE6E9ED); // Map illustration: plots
  static const mapBlock = Color(0xFFE2E6EB); // Map illustration: buildings
  static const whatsappWallpaper = Color(0xFFECE7DF); // WhatsApp chat background in phone mocks (third-party UI)
  static const whatsappBubbleOut = Color(0xFFDCE8FB); // Outgoing chat bubble in the assistant mock
  static const chatBg = Color(0xFFECE9E4); // Chat background in the invitation mock
  static const onNavyMuted = Color(0xFF9AA6BB); // Small caps headings in the footer; disabled text on navy
  static const okOnDark = Color(0xFF8FD3AE); // Success icon on a navy toast
  static const badOnDark = Color(0xFFF1C4BF); // Error text on a navy surface
  static const badIconOnDark = Color(0xFFF4A79F); // Error icon on a navy toast
  static const destructiveHover = Color(0xFF912018); // Destructive button hover
}

class IbhSpace {
  IbhSpace._();
  static const double s4 = 4;
  static const double s8 = 8;
  static const double s12 = 12;
  static const double s16 = 16;
  static const double s20 = 20;
  static const double s24 = 24;
  static const double s32 = 32;
  static const double s40 = 40;
  static const double s48 = 48;
  static const double s64 = 64;
}

class IbhRadius {
  IbhRadius._();
  static const double tag = 6;
  static const double control = 8;
  static const double card = 12;
  static const double dialog = 16;
  static const double sheet = 20;
  static const double device = 24;
  static const double pill = 999;
}

class IbhText {
  IbhText._();
  static const display = TextStyle(fontFamily: 'Inter', fontSize: 56, height: 1.107, fontWeight: FontWeight.w700, letterSpacing: -1.12, color: IbhColors.ink);
  static const h1 = TextStyle(fontFamily: 'Inter', fontSize: 36, height: 1.222, fontWeight: FontWeight.w700, letterSpacing: -0.72, color: IbhColors.ink);
  static const h2 = TextStyle(fontFamily: 'Inter', fontSize: 28, height: 1.286, fontWeight: FontWeight.w700, letterSpacing: -0.56, color: IbhColors.ink);
  static const h3 = TextStyle(fontFamily: 'Inter', fontSize: 20, height: 1.4, fontWeight: FontWeight.w600, letterSpacing: -0.20, color: IbhColors.ink);
  static const bodyLg = TextStyle(fontFamily: 'Inter', fontSize: 16, height: 1.5, fontWeight: FontWeight.w400, letterSpacing: 0, color: IbhColors.slate);
  static const body = TextStyle(fontFamily: 'Inter', fontSize: 15, height: 1.6, fontWeight: FontWeight.w400, letterSpacing: 0, color: IbhColors.slate);
  static const small = TextStyle(fontFamily: 'Inter', fontSize: 14, height: 1.429, fontWeight: FontWeight.w400, letterSpacing: 0, color: IbhColors.slate);
  static const caption = TextStyle(fontFamily: 'Inter', fontSize: 12, height: 1.333, fontWeight: FontWeight.w600, letterSpacing: 0.72, color: IbhColors.slate);
  static const androidBody = TextStyle(fontFamily: 'Inter', fontSize: 15, height: 1.467, fontWeight: FontWeight.w400, letterSpacing: 0, color: IbhColors.slate);
  static const opsBody = TextStyle(fontFamily: 'Inter', fontSize: 13, height: 1.462, fontWeight: FontWeight.w400, letterSpacing: 0, color: IbhColors.slate);
  static const mono = TextStyle(fontFamily: 'JetBrains Mono', fontSize: 13, height: 1.538, fontWeight: FontWeight.w500, letterSpacing: 0, color: IbhColors.slate);
}

enum IbhStatus { ok, warn, bad, neutral, info }

extension IbhStatusColors on IbhStatus {
  Color get bg => const [IbhColors.okBg, IbhColors.warnBg, IbhColors.badBg, IbhColors.neutralBg, IbhColors.infoBg][index];
  Color get fg => const [IbhColors.okFg, IbhColors.warnFg, IbhColors.badFg, IbhColors.neutralFg, IbhColors.infoFg][index];
}

ThemeData ibhTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: IbhColors.navy900,
    onPrimary: IbhColors.white,
    secondary: IbhColors.mist,
    onSecondary: IbhColors.navy900,
    tertiary: IbhColors.accent,
    onTertiary: IbhColors.white,
    error: IbhColors.badFg,
    onError: IbhColors.white,
    surface: IbhColors.white,
    onSurface: IbhColors.ink,
    surfaceContainerHighest: IbhColors.mist,
    outline: IbhColors.lineStrong,
    outlineVariant: IbhColors.line,
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: 'Inter',
    scaffoldBackgroundColor: IbhColors.mist,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    textTheme: const TextTheme(
      headlineLarge: IbhText.h1,
      headlineMedium: IbhText.h2,
      titleLarge: IbhText.h3,
      bodyLarge: IbhText.androidBody,
      bodyMedium: IbhText.androidBody,
      bodySmall: IbhText.small,
      labelSmall: IbhText.caption,
    ),
    appBarTheme: const AppBarTheme(backgroundColor: IbhColors.white, foregroundColor: IbhColors.ink, elevation: 0, scrolledUnderElevation: 0),
    filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(
      backgroundColor: IbhColors.navy900, foregroundColor: IbhColors.white, minimumSize: const Size.fromHeight(48),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(IbhRadius.control)),
      textStyle: const TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600))),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(
      foregroundColor: IbhColors.navy900, minimumSize: const Size.fromHeight(48), side: const BorderSide(color: IbhColors.frame),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(IbhRadius.control)))),
    inputDecorationTheme: InputDecorationTheme(
      filled: true, fillColor: IbhColors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(IbhRadius.control), borderSide: const BorderSide(color: IbhColors.lineStrong)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(IbhRadius.control), borderSide: const BorderSide(color: IbhColors.accent, width: 2)),
      errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(IbhRadius.control), borderSide: const BorderSide(color: IbhColors.badFg)),
    ),
    cardTheme: CardThemeData(color: IbhColors.white, elevation: 0, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(IbhRadius.card), side: const BorderSide(color: IbhColors.line))),
    snackBarTheme: const SnackBarThemeData(backgroundColor: IbhColors.navy900, contentTextStyle: TextStyle(fontFamily: 'Inter', fontSize: 15, color: IbhColors.white), behavior: SnackBarBehavior.floating),
    dividerTheme: const DividerThemeData(color: IbhColors.line, thickness: 1),
  );
}
