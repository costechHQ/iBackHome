"use client";

import { MessageCircle, Send, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { api, call } from "@/common/api/client";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";

import {
  askable,
  contactLinks,
  describeAssistantError,
  DISCLAIMER,
  MAX_QUESTION,
  SUGGESTIONS,
  type ChatMessage,
} from "./assistant";

// The chat box on the home page and the Contact page (ADR 0006): a round button bottom-right that opens a panel
// (full screen on a phone). Answers come from the backend's vetted text; nothing typed is stored, and the
// conversation lives only in this component, so it is gone when the tab closes. "Talk to a person" is always
// one tap away.

function ContactButtons() {
  return (
    <div className="flex flex-wrap gap-2" aria-label="Talk to a person">
      {contactLinks().map((l) => (
        <Button key={l.label} asChild variant="outline" className="type-small min-h-10 px-3">
          <a href={l.href} {...(l.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
            {l.label}
          </a>
        </Button>
      ))}
    </div>
  );
}

export function AssistantWidget() {
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const next = useRef(1);
  const launcher = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const end = useRef<HTMLDivElement>(null);

  // Focus the question box on open; once closed, put focus back on the round button (which is only on the page
  // while the panel is closed, so this runs after it has appeared).
  const restoreFocus = useRef(false);
  useEffect(() => {
    if (open) input.current?.focus();
    else if (restoreFocus.current) {
      restoreFocus.current = false;
      launcher.current?.focus();
    }
  }, [open]);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages, pending, problem]);

  function close() {
    restoreFocus.current = true;
    setOpen(false);
  }

  async function send(question: string) {
    const trimmed = question.trim();
    if (pending || !askable(trimmed)) return;
    setProblem(null);
    setText("");
    setMessages((m) => [...m, { id: next.current++, role: "user", text: trimmed }]);
    setPending(true);
    try {
      const reply = await call(api().POST("/api/v1/assistant/chat", { body: { message: trimmed } }));
      setMessages((m) => [
        ...m,
        {
          id: next.current++,
          role: "assistant",
          text: reply.answer,
          related: reply.related.map((r) => r.question),
          handoff: reply.handoff,
        },
      ]);
    } catch (error) {
      setProblem(describeAssistantError(error));
    } finally {
      setPending(false);
      input.current?.focus();
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
          className="fixed right-4 bottom-4 z-40 flex size-14 items-center justify-center rounded-pill bg-navy-900 text-white shadow-dialog transition-colors hover:bg-primary-hover sm:right-6 sm:bottom-6"
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
          className="fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:right-6 sm:bottom-6 sm:h-144 sm:w-96 sm:rounded-card sm:border sm:border-line sm:shadow-dialog"
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
              className="flex size-10 items-center justify-center rounded-pill hover:bg-mist"
            >
              <X aria-hidden strokeWidth={1.75} className="size-5" />
            </button>
          </header>

          <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
            <p className="type-small rounded-card bg-canvas px-3 py-2 text-slate">{DISCLAIMER}</p>
            <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-col gap-3">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={cn("flex flex-col gap-2", m.role === "user" ? "items-end" : "items-start")}
                >
                  <p
                    className={cn(
                      "max-w-full rounded-card px-3 py-2 whitespace-pre-line",
                      m.role === "user" ? "bg-navy-900 text-white" : "bg-mist text-ink",
                    )}
                  >
                    {m.text}
                  </p>
                  {m.role === "assistant" && m.handoff ? <ContactButtons /> : null}
                  {m.role === "assistant" && m.related?.length ? (
                    <div className="flex flex-col items-start gap-1.5" aria-label="Related questions">
                      {m.related.map((q) => (
                        <button
                          key={q}
                          type="button"
                          disabled={pending}
                          onClick={() => void send(q)}
                          className="type-small rounded-pill border border-line bg-white px-3 py-1.5 text-left text-ink hover:bg-mist disabled:text-muted"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {pending ? (
                <p className="type-small text-muted" role="status">
                  Looking that up…
                </p>
              ) : null}
              {problem ? (
                <div className="flex flex-col gap-2">
                  <p role="alert" className="rounded-card bg-bad-bg px-3 py-2 text-ink">
                    {problem}
                  </p>
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
                    onClick={() => void send(s)}
                    disabled={pending}
                    className="type-small rounded-pill border border-line bg-white px-3 py-2 text-left text-ink hover:bg-mist disabled:text-muted"
                  >
                    {s}
                  </button>
                ))}
              </div>
            ) : null}
            <div ref={end} />
          </div>

          <div className="flex flex-col gap-2 border-t border-line px-4 py-3">
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                void send(text);
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
                className="min-h-11 flex-1 rounded-control border border-line-strong bg-white px-3 text-ink placeholder:text-muted"
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
