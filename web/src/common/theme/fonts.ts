import localFont from "next/font/local";

// Self-hosted copies of Docs/design/05-assets/fonts (scripts/sync-tokens.sh), split by the unicode ranges of the
// handoff's tokens.css (written inline: next/font only accepts literal options). latin-ext is needed for ₦ (U+20A6). No generated fallback family (adjustFontFallback: false), so
// the stack in theme.css reaches latin-ext before the system fonts.
export const interLatin = localFont({
  src: [
    { path: "./fonts/inter-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/inter-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/inter-latin-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/inter-latin-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-inter-latin",
  display: "swap",
  adjustFontFallback: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
    },
  ],
});

export const interLatinExt = localFont({
  src: [
    { path: "./fonts/inter-latin-ext-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/inter-latin-ext-500-normal.woff2", weight: "500", style: "normal" },
    { path: "./fonts/inter-latin-ext-600-normal.woff2", weight: "600", style: "normal" },
    { path: "./fonts/inter-latin-ext-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-inter-latin-ext",
  display: "swap",
  adjustFontFallback: false,
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
    },
  ],
});

export const monoLatin = localFont({
  src: [
    { path: "./fonts/jetbrains-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/jetbrains-mono-latin-500-normal.woff2", weight: "500", style: "normal" },
  ],
  variable: "--font-mono-latin",
  display: "swap",
  adjustFontFallback: false,
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
    },
  ],
});

export const monoLatinExt = localFont({
  src: [
    { path: "./fonts/jetbrains-mono-latin-ext-400-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/jetbrains-mono-latin-ext-500-normal.woff2", weight: "500", style: "normal" },
  ],
  variable: "--font-mono-latin-ext",
  display: "swap",
  adjustFontFallback: false,
  preload: false,
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0100-02AF,U+0304,U+0308,U+0329,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
    },
  ],
});

/** Class names that define the four font variables; put them on <html>. */
export const fontVariables = [interLatin, interLatinExt, monoLatin, monoLatinExt]
  .map((f) => f.variable)
  .join(" ");
