"use client";

import { ChevronDown, Search } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { COMMON_ISO, countryByIso, searchCountries, type Country } from "@/common/countries";
import { cn } from "@/common/ui/cn";

// The calling-code picker beside the phone number (WEB-PUBLIC-010 "Country selector"): search by name or code,
// common countries first. A button opens a search box over a listbox; arrow keys move, Enter picks, Escape
// closes and returns focus to the button.

export function CountryPicker({
  value,
  onChange,
  labelId,
}: {
  value: string;
  onChange: (iso: string) => void;
  labelId: string;
}) {
  const ids = { list: useId(), search: useId() };
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const button = useRef<HTMLButtonElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const current = countryByIso(value);

  const options = useMemo(() => {
    const found = searchCountries(query);
    if (query.trim()) return found.map((c) => ({ country: c, common: false }));
    const common = COMMON_ISO.map((iso) => countryByIso(iso)).filter((c): c is Country => Boolean(c));
    return [
      ...common.map((c) => ({ country: c, common: true })),
      ...found
        .filter((c) => !COMMON_ISO.includes(c.iso as never))
        .map((c) => ({ country: c, common: false })),
    ];
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const pick = (country: Country) => {
    onChange(country.iso);
    setOpen(false);
    setQuery("");
    button.current?.focus();
  };

  const keys = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const option = options[active];
      if (option) pick(option.country);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      button.current?.focus();
    }
  };

  const optionId = (i: number) => `${ids.list}-${i}`;

  return (
    <div ref={root} className="relative flex-none">
      <button
        ref={button}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        // "Phone number GB +44, United Kingdom": the field label, then what the button shows.
        aria-labelledby={`${labelId} ${ids.list}-current`}
        onClick={() => {
          setOpen((o) => !o);
          setActive(0);
        }}
        className="flex min-h-12 items-center gap-1.5 rounded-control border border-line-strong bg-mist px-3 font-semibold text-ink"
      >
        <span id={`${ids.list}-current`}>
          {current ? `${current.iso} +${current.dial}` : "Code"}
          <span className="sr-only">{current ? `, ${current.name}` : ""}</span>
        </span>
        <ChevronDown aria-hidden strokeWidth={1.75} className="size-4" />
      </button>
      {open ? (
        <div className="absolute top-full left-0 z-30 mt-1 flex w-72 flex-col overflow-hidden rounded-card border border-line bg-white shadow-raised">
          <div className="flex items-center gap-2 border-b border-line px-3">
            <Search aria-hidden strokeWidth={1.75} className="size-4 text-muted" />
            <label htmlFor={ids.search} className="sr-only">
              Search country or code
            </label>
            <input
              id={ids.search}
              autoFocus
              role="combobox"
              aria-expanded
              aria-controls={ids.list}
              aria-activedescendant={options.length ? optionId(active) : undefined}
              aria-autocomplete="list"
              placeholder="Search country or code"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
              }}
              onKeyDown={keys}
              className="min-h-11 flex-1 bg-transparent text-ink placeholder:text-muted"
            />
          </div>
          <ul id={ids.list} role="listbox" aria-label="Countries" className="max-h-72 overflow-y-auto py-1">
            {options.map(({ country, common }, i) => (
              <li
                key={`${common ? "common" : "all"}-${country.iso}`}
                id={optionId(i)}
                role="option"
                aria-selected={country.iso === value}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(country)}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  "flex min-h-10 cursor-pointer items-center justify-between gap-3 px-3 text-ink",
                  i === active && "bg-row-highlight",
                  common && i === COMMON_ISO.length - 1 && !query && "border-b border-line",
                )}
              >
                <span>
                  {i === 0 && common ? <span className="sr-only">Common: </span> : null}
                  {country.name}
                </span>
                <span className="ibh-tabular text-slate">+{country.dial}</span>
              </li>
            ))}
            {!options.length ? <li className="px-3 py-2 text-slate">No country matches.</li> : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
