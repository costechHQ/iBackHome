import { cn } from "./cn";

// The wordmark (Docs/design/05-assets/logo): a house outline with an eye inside, in a rounded square, plus
// "iBackHome" in Inter 700. Same geometry as the handoff SVGs, coloured with tokens: navy square on light
// surfaces, white square on navy. Only navy and white, never recoloured.

export function Mark({ onDark, className }: { onDark?: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={cn("size-8 flex-none", className)}>
      <rect width="40" height="40" rx="10" className={onDark ? "fill-white" : "fill-navy-900"} />
      <g
        transform="translate(8 8)"
        fill="none"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={onDark ? "stroke-navy-900" : "stroke-white"}
      >
        <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
        <path d="M6.5 15c1.5-2.1 3.3-3.2 5.5-3.2s4 1.1 5.5 3.2c-1.5 2.1-3.3 3.2-5.5 3.2s-4-1.1-5.5-3.2z" />
        <circle cx="12" cy="15" r="1.3" stroke="none" className={onDark ? "fill-navy-900" : "fill-white"} />
      </g>
    </svg>
  );
}

export function Wordmark({ onDark, className }: { onDark?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Mark onDark={onDark} />
      <span className={cn("type-h3 font-bold", onDark ? "text-white" : "text-ink")}>iBackHome</span>
    </span>
  );
}
