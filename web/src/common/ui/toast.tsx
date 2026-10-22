"use client";

import * as ToastPrimitive from "@radix-ui/react-toast";
import { CircleCheck, X, type LucideIcon } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

// Toast (components.md, Feedback; WEB-CLIENT-024 frame 9): confirms something that already happened. Navy,
// bottom right, 6 s (Radix pauses the timer on hover and focus), announced to screen readers. Never the only
// record of an important event, and never an "Undo" on money.

export type ToastInput = {
  message: string;
  icon?: LucideIcon;
  action?: { label: string; onClick: () => void };
};
type Item = ToastInput & { id: number };

const ToastContext = createContext<(toast: ToastInput) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export const TOAST_DURATION_MS = 6_000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const show = useCallback((toast: ToastInput) => {
    setItems((current) => [...current, { ...toast, id: Date.now() + Math.random() }]);
  }, []);
  const remove = (id: number) => setItems((current) => current.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={show}>
      <ToastPrimitive.Provider duration={TOAST_DURATION_MS} label="Notification">
        {children}
        {items.map(({ id, message, icon: Icon = CircleCheck, action }) => (
          <ToastPrimitive.Root
            key={id}
            onOpenChange={(open) => !open && remove(id)}
            className="ibh-on-navy type-small flex items-center gap-3 rounded-control bg-navy-900 px-4 py-3.5 text-white shadow-raised"
          >
            <Icon aria-hidden strokeWidth={1.75} className="size-5 flex-none text-x-ok-on-dark" />
            <ToastPrimitive.Description className="flex-1">{message}</ToastPrimitive.Description>
            {action ? (
              <ToastPrimitive.Action altText={action.label} asChild>
                <button
                  type="button"
                  onClick={action.onClick}
                  className="font-semibold text-focus-on-dark underline"
                >
                  {action.label}
                </button>
              </ToastPrimitive.Action>
            ) : null}
            <ToastPrimitive.Close
              aria-label="Dismiss"
              className="flex size-8 items-center justify-center rounded-tag text-navy-200 hover:text-white"
            >
              <X aria-hidden strokeWidth={2} className="size-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed right-0 bottom-0 z-50 flex w-full max-w-md flex-col gap-2 p-4 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
