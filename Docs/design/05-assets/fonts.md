# Fonts

| Family | Weights | Use |
|---|---|---|
| Inter | 400, 500, 600, 700 | All UI text (web and Android) |
| JetBrains Mono | 400, 500 | IDs and references (EV-, R-, P-, T-, O-, D-) |

Tabular figures (`font-variant-numeric: tabular-nums`) for money, counts and times. Headings use letter-spacing −0.02em.

## Files in this package

`05-assets/fonts/` holds WOFF2 files from Fontsource (latin and latin-ext subsets, so ₦ and other symbols render) with the SIL Open Font License texts. `01-design-system/tokens.css` declares them with `@font-face`, which is why every `screen.html` opens offline with the right fonts.

## Loading them in the apps

- **React + Vite**: `npm i @fontsource/inter @fontsource/jetbrains-mono` and import `@fontsource/inter/400.css` … `700.css`, `@fontsource/jetbrains-mono/400.css` and `500.css` in the entry file; or copy the `@font-face` rules from `tokens.css` and serve the WOFF2 files yourself. Avoid a runtime Google Fonts request if the repo has a CSP or offline requirement.
- **Flutter**: add the Inter and JetBrains Mono TTF files (download from the Inter and JetBrains Mono releases or Google Fonts; WOFF2 isn't supported by Flutter) under `mobile/assets/fonts/` and declare them in `pubspec.yaml` with weights 400/500/600/700; `flutter_theme.dart` sets `fontFamily: 'Inter'`. Keep the APK small for 2 GB RAM devices: only these weights.
- Fallback stack: `'Inter', 'Segoe UI', Roboto, Arial, sans-serif` (Roboto on Android).
