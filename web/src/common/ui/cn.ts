import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// tailwind-merge has to know our own utilities: the type-* styles (theme.css) are one group, so a later
// type-small replaces an earlier type-body instead of both staying on the element.
const twMerge = extendTailwindMerge<"type-style">({
  extend: {
    classGroups: {
      "type-style": [
        { type: ["display", "h1", "h2", "h3", "body-lg", "body", "small", "caption", "ops-body", "mono"] },
      ],
    },
  },
});

/** Joins class names; later Tailwind classes win over earlier ones of the same kind. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
