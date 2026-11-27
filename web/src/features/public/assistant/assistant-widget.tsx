"use client";

import { MessageCircle, RotateCw, Send, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { api, call } from "@/common/api/client";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";

import {
  ANSWER_TIMEOUT_MS,
  askable,
  cacheKey,
  contactLinks,
  describeAssistantError,
  DISCLAIMER,
  MAX_QUESTION,
  retryable,
  SUGGESTIONS,
  type ChatMessage,
} from "./assistant";

// The chat box on the home page and the Contact page (ADR 0006): a round button bottom-right that opens a panel
// (the whole screen on a phone). Answers come from the backend's vetted text; nothing typed is stored, and the
// conversation lives only in this component, so it is gone when the tab closes. "Talk to a person" is always
// one tap away.
//
// Built to feel instant on any screen: your question appears the moment you send it, a question asked before is
// answered from memory with no trip to the server, a slow answer gives up after 15 seconds with a "Try again",
// the panel uses the real screen height (the on-screen keyboard doesn't cover the box), a tapped suggestion
// doesn't pop the keyboard over the answer, and motion stops for visitors who ask for less of it.

type Reply = { answer: string; related: string[]; handoff: boolean };

function ContactButtons() {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Talk to a person">
      {contactLinks().map((l) => (
        <Button key={l.label} asChild variant="outline" className="type-small min-h-11 px-3">
          <a href={l.href} {...(l.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
            {l.label}
          </a>
        </Button>
      ))}
    </div>
  );
}

function ContactLine() {
  const links = contactLinks();
  return (
    <>
      {links.map((l, i) => (
        <span key={l.label}>
          {i > 0 ? " · " : ""}
          <a
            href={l.href}
            className="text-accent underline"
            {...(l.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
          >
            {l.label}
          </a>
        </span>
      ))}
    </>
  );
}

function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function AssistantWidget() {
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<{ text: string; retry: string | null } | null>(null);
  const next = useRef(1);
  const cache = useRef(new Map<string, Reply>());
  const launcher = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const restoreFocus = useRef(false);

  // Focus the question box on open; once closed, put focus back on the round button (which is only on the page
  // while the panel is closed, so this runs after it has appeared).
  useEffect(() => {
    if (open) input.current?.focus();
    else if (restoreFocus.current) {
      restoreFocus.current = false;
      launcher.current?.focus();
    }
  }, [open]);

  // On a phone the panel is the whole screen: don't let the page behind it scroll.
  useEffect(() => {
    if (!open || typeof window.matchMedia !== "function" || !window.matchMedia("(max-width: 639px)").matches)
      return;
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = before;
    };
  }, [open]);

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end", behavior: prefersReducedMotion() ? "auto" : "smooth" });
  }, [messages, pending, problem]);

  function close() {
    restoreFocus.current = true;
    setOpen(false);
  }

  function addAnswer(reply: Reply) {
    setMessages((m) => [
      ...m,
      {
        id: next.current++,
        role: "assistant",
        text: reply.answer,
        related: reply.related,
        handoff: reply.handoff,
      },
    ]);
  }

  /** `typed`: the visitor typed it (keep the keyboard ready); a tapped suggestion leaves the answer in view. */
  async function send(question: string, typed: boolean) {
    const trimmed = question.trim();
    if (pending || !askable(trimmed)) return;
    setProblem(null);
    setText("");
    setMessages((m) => [...m, { id: next.current++, role: "user", text: trimmed }]);

    const known = cache.current.get(cacheKey(trimmed));
    if (known) {
      addAnswer(known); // asked before: answered at once, no trip to the server
      if (typed) input.current?.focus();
      return;
    }

    setPending(true);
    try {
      const response = await call(
        api().POST("/api/v1/assistant/chat", {
          body: { message: trimmed },
          signal: AbortSignal.timeout(ANSWER_TIMEOUT_MS),
        }),
      );
      const reply: Reply = {
        answer: response.answer,
        related: response.related.map((r) => r.question),
        handoff: response.handoff,
      };
      cache.current.set(cacheKey(trimmed), reply);
      addAnswer(reply);
    } catch (error) {
      setProblem({ text: describeAssistantError(error), retry: retryable(error) ? trimmed : null });
    } finally {
      setPending(false);
      if (typed) input.current?.focus();
    }
  }

  return (
    <>
      {!open ? (
        <button
          ref={launcher}
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Ask a question"
          className="ibh-chat-launcher fixed right-4 bottom-4 z-40 flex size-14 items-center justify-center rounded-pill bg-navy-900 text-white shadow-dialog transition-colors hover:bg-primary-hover sm:right-6 sm:bottom-6"
        >
          <MessageCircle aria-hidden strokeWidth={1.75} className="size-7" />
        </button>
      ) : (
        <div
          role="dialog"
          aria-labelledby={titleId}
          onKeyDown={(e) => {
            if (e.key === "Escape") close();
          }}
          className="ibh-chat-panel fixed inset-x-0 top-0 z-50 flex h-dvh flex-col bg-white sm:inset-x-auto sm:top-auto sm:right-6 sm:bottom-6 sm:h-144 sm:max-h-9/10 sm:w-96 sm:rounded-card sm:border sm:border-line sm:shadow-dialog md:w-104"
        >
          <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <div className="flex flex-col">
              <h2 id={titleId} className="type-h3 text-ink">
                Ask iBackHome
              </h2>
              <p className="type-small text-muted">Automated assistant</p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Close the chat"
              className="flex size-11 items-center justify-center rounded-pill hover:bg-mist"
            >
              <X aria-hidden strokeWidth={1.75} className="size-5" />
            </button>
          </header>

          <div className="flex flex-1 flex-col gap-3 overflow-y-auto overscroll-contain px-4 py-4">
            <p className="type-small rounded-card bg-canvas px-3 py-2 text-slate">{DISCLAIMER}</p>
            <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-3">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn(
                    "ibh-chat-message flex flex-col gap-2",
                    m.role === "user" ? "items-end" : "items-start",
                  )}
                >
                  <p
                    className={cn(
                      "max-w-full rounded-card px-3 py-2 break-words whitespace-pre-line",
                      m.role === "user" ? "bg-navy-900 text-white" : "bg-mist text-ink",
                    )}
                  >
                    {m.text}
                  </p>
                  {m.role === "assistant" && m.handoff ? <ContactButtons /> : null}
                  {m.role === "assistant" && m.related?.length ? (
                    <div
                      className="flex flex-col items-start gap-1.5"
                      role="group"
                      aria-label="Related questions"
                    >
                      {m.related.map((q) => (
                        <button
                          key={q}
                          type="button"
                          disabled={pending}
                          onClick={() => void send(q, false)}
                          className="type-small min-h-11 rounded-pill border border-line bg-white px-3 py-2 text-left text-ink hover:bg-mist disabled:text-muted"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {pending ? (
                <p className="type-small ibh-chat-message flex items-center gap-2 text-muted" role="status">
                  <span aria-hidden className="flex gap-1">
                    <span className="ibh-chat-dot size-1.5 rounded-pill bg-slate" />
                    <span className="ibh-chat-dot size-1.5 rounded-pill bg-slate [--ibh-delay:150ms]" />
                    <span className="ibh-chat-dot size-1.5 rounded-pill bg-slate [--ibh-delay:300ms]" />
                  </span>
                  Looking that up…
                </p>
              ) : null}
              {problem ? (
                <div className="ibh-chat-message flex flex-col gap-2">
                  <p role="alert" className="rounded-card bg-bad-bg px-3 py-2 text-ink">
                    {problem.text}
                  </p>
                  {problem.retry ? (
                    <Button
                      variant="secondary"
                      className="type-small min-h-11 self-start px-3"
                      onClick={() => void send(problem.retry ?? "", false)}
                    >
                      <RotateCw aria-hidden strokeWidth={1.75} className="size-4" />
                      Try again
                    </Button>
                  ) : null}
                  <ContactButtons />
                </div>
              ) : null}
            </div>
            {!messages.length ? (
              <div className="flex flex-col gap-2">
                <p className="type-small font-semibold text-ink">Try asking</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void send(s, false)}
                    disabled={pending}
                    className="type-small min-h-11 rounded-pill border border-line bg-white px-3 py-2 text-left text-ink hover:bg-mist disabled:text-muted"
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}
            <div ref={end} />
          </div>

          <div className="ibh-chat-safe flex flex-col gap-2 border-t border-line px-4 pt-3">
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void send(text, true);
              }}
            >
              <label htmlFor={`${titleId}-q`} className="sr-only">
                Your question
              </label>
              <input
                id={`${titleId}-q`}
                ref={input}
                value={text}
                maxLength={MAX_QUESTION}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ask a question"
                autoComplete="off"
                enterKeyHint="send"
                className="min-h-11 flex-1 rounded-control border border-line-strong bg-white px-3 text-base text-ink placeholder:text-muted"
              />
              <Button
                type="submit"
                aria-label="Send"
                disabled={!askable(text) || pending}
                className="size-11 px-0"
              >
                <Send aria-hidden strokeWidth={1.75} className="size-5" />
              </Button>
            </form>
            <p className="type-small text-muted">
              Need a person? <ContactLine />
            </p>
          </div>
        </div>
      )}
    </>
  );
}
