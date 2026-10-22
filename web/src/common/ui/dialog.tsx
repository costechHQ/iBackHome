"use client";

import * as AlertPrimitive from "@radix-ui/react-alert-dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useRef, type ReactNode } from "react";

import { Button } from "./button";
import { cn } from "./cn";

// Dialog and alert dialog (components.md, Overlays; WEB-CLIENT-024 frames 10 and 11). Radix moves focus in,
// traps it, and (useReturnFocus) returns it to the button that opened the dialog. Escape closes a Dialog; an AlertDialog about
// money ignores Escape and an outside click, so money is only moved or kept by a deliberate button press.
// The safe choice is on the left and named for what it keeps; destructive buttons appear only here.

const overlay = "fixed inset-0 z-40 bg-ink/50";

/**
 * Our dialogs are opened by a screen's own button, not a Radix Trigger, so Radix doesn't know where focus came
 * from. Remember the focused element as the dialog opens and put focus back there when it closes.
 */
function useReturnFocus() {
  const returnTo = useRef<HTMLElement | null>(null);
  return {
    onOpenAutoFocus: () => {
      returnTo.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    },
    onCloseAutoFocus: (event: Event) => {
      if (returnTo.current?.isConnected) {
        event.preventDefault();
        returnTo.current.focus();
      }
    },
  };
}
const panel =
  "fixed inset-x-4 top-1/2 z-50 mx-auto flex max-w-md -translate-y-1/2 flex-col gap-3 " +
  "rounded-dialog bg-white p-6 shadow-dialog";

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
}) {
  const focus = useReturnFocus();
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlay} />
        {/* Without a description Radix needs aria-describedby={undefined} said explicitly. */}
        <DialogPrimitive.Content
          {...focus}
          className={panel}
          {...(description ? {} : { "aria-describedby": undefined })}
        >
          <DialogPrimitive.Title className="type-h3 text-ink">{title}</DialogPrimitive.Title>
          {description ? (
            <DialogPrimitive.Description className="text-slate">{description}</DialogPrimitive.Description>
          ) : null}
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  onConfirm,
  destructive,
  aboutMoney,
  busy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  /** Name it for what it keeps ("Keep invitation"). */
  cancelLabel?: string;
  onConfirm: () => void;
  destructive?: boolean;
  /** Money is moved or held: Escape and an outside click do nothing. */
  aboutMoney?: boolean;
  busy?: boolean;
}) {
  const focus = useReturnFocus();
  const block = (event: Event) => {
    if (aboutMoney || busy) event.preventDefault();
  };
  return (
    <AlertPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <AlertPrimitive.Portal>
        <AlertPrimitive.Overlay className={overlay} />
        <AlertPrimitive.Content {...focus} className={panel} onEscapeKeyDown={block}>
          <AlertPrimitive.Title className="type-h3 text-ink">{title}</AlertPrimitive.Title>
          <AlertPrimitive.Description className="text-slate">{description}</AlertPrimitive.Description>
          <div className="mt-2 flex flex-wrap justify-end gap-3">
            <AlertPrimitive.Cancel asChild>
              <Button variant="secondary" size="lg" disabled={busy}>
                {cancelLabel}
              </Button>
            </AlertPrimitive.Cancel>
            {/* Not AlertPrimitive.Action: the dialog stays open (busy) until the write finishes. */}
            <Button
              variant={destructive ? "destructive" : "primary"}
              size="lg"
              loading={busy}
              onClick={onConfirm}
              className={cn(busy && "pointer-events-none")}
            >
              {confirmLabel}
            </Button>
          </div>
        </AlertPrimitive.Content>
      </AlertPrimitive.Portal>
    </AlertPrimitive.Root>
  );
}
