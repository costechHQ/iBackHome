import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "./cn";

// Buttons (components.md, Controls). One primary per view. Destructive appears only inside a confirmation
// dialog, with the safe choice on its left. 44px minimum target on the web; full width on mobile where designed.
export const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 rounded-control border border-transparent px-4",
    "font-semibold whitespace-nowrap transition-colors",
    // Focus: the token stylesheet draws one visible outline on every control (accent; on-dark inside .ibh-on-navy).
    "disabled:cursor-not-allowed aria-busy:cursor-progress",
  ],
  {
    variants: {
      variant: {
        primary: "bg-primary text-white hover:bg-primary-hover disabled:bg-neutral-bg disabled:text-muted",
        // Mist on light surfaces; the bordered white version sits next to a primary on error pages.
        secondary: "bg-mist text-navy-900 hover:bg-placeholder disabled:text-muted",
        outline: "border-frame bg-white text-ink hover:bg-mist disabled:text-muted",
        // On a navy panel ("Raise a dispute" next to "Approve release" on the approval card). Put .ibh-on-navy on
        // the panel so the focus outline switches to the on-dark colour.
        "outline-on-navy": "border-white bg-transparent text-white hover:bg-navy-800",
        "white-on-navy": "bg-white text-navy-900 hover:bg-mist",
        text: "px-2 text-accent underline-offset-2 hover:text-accent-hover hover:underline",
        destructive:
          "bg-bad-fg text-white hover:bg-x-destructive-hover disabled:bg-neutral-bg disabled:text-muted",
      },
      size: {
        md: "min-h-target type-small font-semibold",
        lg: "min-h-12 type-body font-semibold",
      },
      block: { true: "w-full" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type Props = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    /** Shows a spinner, keeps the label, and blocks a second click while a write is in flight. */
    loading?: boolean;
    /** Renders the child element (a link) with button styles. */
    asChild?: boolean;
  };

export function Button({
  className,
  variant,
  size,
  block,
  loading,
  asChild,
  disabled,
  children,
  ...rest
}: Props) {
  const classes = cn(buttonVariants({ variant, size, block }), loading && "opacity-90", className);
  if (asChild) {
    // Slot needs exactly one child element (the link): no spinner, no disabled state on a link.
    return (
      <Slot className={classes} {...rest}>
        {children}
      </Slot>
    );
  }
  // Loading keeps the button's own colour (the sheet's "loading" state, not "disabled") and focus, but any
  // click or key press is ignored until the write finishes.
  const { onClick, ...buttonProps } = rest;
  return (
    <button
      type="button"
      className={classes}
      disabled={disabled}
      aria-disabled={loading || undefined}
      aria-busy={loading || undefined}
      onClick={(event) => {
        if (loading) {
          event.preventDefault();
          return;
        }
        onClick?.(event);
      }}
      {...buttonProps}
    >
      {loading ? <LoaderCircle aria-hidden className="size-4 animate-spin" /> : null}
      {children}
    </button>
  );
}
