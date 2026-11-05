import Image from "next/image";
import Link from "next/link";

import { cn } from "./cn";

// The brand logo (Docs/design/05-assets/logo, updated 2026-10-23): the house with an eye above the waves, and
// "iBackHome" beneath. Two artworks, never recoloured: blue on light surfaces, white on the primary navy.
// They are PNGs (no vector files yet), shown at most at their natural size. `Mark` is the house and eye alone,
// for tight spaces (the client's phone top bar).

const LOGO = {
  light: { src: "/brand/ibackhome-logo-on-light.png", width: 485, height: 263 },
  dark: { src: "/brand/ibackhome-logo-on-dark.png", width: 499, height: 271 },
} as const;

const MARK = {
  light: "/brand/ibackhome-mark-on-light.png",
  dark: "/brand/ibackhome-mark-on-dark.png",
} as const;

const HEIGHT = { md: "h-11", lg: "h-16" } as const;

export function Mark({ onDark, className }: { onDark?: boolean; className?: string }) {
  return (
    <Image
      src={onDark ? MARK.dark : MARK.light}
      alt="iBackHome"
      width={512}
      height={512}
      className={cn("size-10 flex-none", className)}
    />
  );
}

export function Wordmark({
  onDark,
  size = "md",
  className,
}: {
  onDark?: boolean;
  size?: keyof typeof HEIGHT;
  className?: string;
}) {
  const logo = onDark ? LOGO.dark : LOGO.light;
  return (
    <Image
      src={logo.src}
      alt="iBackHome"
      width={logo.width}
      height={logo.height}
      priority
      className={cn("w-auto flex-none", HEIGHT[size], className)}
    />
  );
}

/** Wherever the logo appears it links to the index page (/). A signed-in visitor is sent on from there to
 *  their own portal (proxy.ts), a signed-out one sees the website. Put the logo inside this rather than
 *  writing a Link around it. */
export function BrandLink({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Link href="/" aria-label="iBackHome home" className={cn("rounded-control", className)}>
      {children}
    </Link>
  );
}
