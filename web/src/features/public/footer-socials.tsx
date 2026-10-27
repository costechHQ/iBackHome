import type { ReactNode } from "react";

// iBackHome's social accounts, shown as round icon buttons in the footer. The brand icons are drawn here
// because the icon set has none. Each opens in a new tab.

type Social = { name: string; href: string; handle: string; icon: ReactNode };

const SOCIALS: readonly Social[] = [
  {
    name: "Instagram",
    handle: "@iback.home",
    href: "https://www.instagram.com/iback.home/",
    icon: (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="size-5"
      >
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="0.6" fill="currentColor" />
      </svg>
    ),
  },
  {
    name: "X",
    handle: "@iBackHome1",
    href: "https://x.com/iBackHome1",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="size-4">
        <path d="M18 3h3l-7.5 8.5L22 21h-6.5l-5-6.2L5 21H2l8-9.2L2 3h6.6l4.6 5.7L18 3Zm-1.1 16h1.7L7.2 4.9H5.4L16.9 19Z" />
      </svg>
    ),
  },
  {
    name: "Facebook",
    handle: "iBackHome",
    href: "https://www.facebook.com/share/1Fnj4uPq5b/?mibextid=wwXIfr",
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="size-5">
        <path d="M14 8V6.5c0-.8.4-1 1-1h2V2h-3c-3 0-4.5 1.8-4.5 4.5V8H7v3.5h2.5V22H14V11.5h2.8L17.5 8H14Z" />
      </svg>
    ),
  },
];

export function FooterSocials() {
  return (
    <ul className="flex items-center gap-3" aria-label="iBackHome on social media">
      {SOCIALS.map(({ name, handle, href, icon }) => (
        <li key={name}>
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`iBackHome on ${name} (${handle})`}
            className="flex size-10 items-center justify-center rounded-full border border-navy-700 bg-navy-800 text-white transition duration-300 hover:-translate-y-0.5 hover:bg-white hover:text-navy-900"
          >
            {icon}
          </a>
        </li>
      ))}
    </ul>
  );
}
