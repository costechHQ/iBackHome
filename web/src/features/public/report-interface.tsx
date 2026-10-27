import { CalendarClock, ChevronRight, FileText, Lock } from "lucide-react";
import Image from "next/image";

import { PHOTOS, type Photo } from "./photos";
import { Reveal } from "./reveal";

// An illustration of the weekly report as the client sees it (WEB-PUBLIC-002): AI drafts it from the project's
// own evidence, the supervisor checks it, and every point links to the photo behind it. The content is sample
// text with no names or amounts (PACKAGE-REPORT W-37) and the card says so. It stretches to the height of the
// column beside it.

const DONE: readonly { photo: Photo; text: string }[] = [
  { photo: PHOTOS.blockwork, text: "Ground-floor blockwork finished" },
  { photo: PHOTOS.sandcrete, text: "Blocks and sand delivered and counted" },
  { photo: PHOTOS.formwork, text: "Formwork and steel checked before the pour" },
];

export function ReportInterface() {
  return (
    <figure
      aria-label="Illustration of a weekly report"
      className="flex size-full flex-col gap-5 rounded-card border border-line bg-white p-5 shadow-raised sm:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 font-semibold text-ink">
          <span className="flex size-9 items-center justify-center rounded-control bg-mist text-navy-900">
            <FileText aria-hidden strokeWidth={1.75} className="size-5" />
          </span>
          Your weekly report
        </p>
        <span className="type-small flex items-center gap-1 text-muted">
          <CalendarClock aria-hidden strokeWidth={1.75} className="size-4" />
          Every Friday
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="type-caption rounded-pill bg-accent-tint px-2 py-0.5 tracking-normal text-info-fg">
          AI-generated report
        </span>
        <span className="type-caption rounded-pill bg-ok-bg px-2 py-0.5 tracking-normal text-ok-fg">
          Reviewed by your supervisor
        </span>
      </div>

      <p className="text-slate">
        Blockwork on the ground floor was finished and verified on site this week. Steel for the slab is on
        site and one milestone is waiting for your approval.
      </p>

      <div className="flex flex-col gap-2">
        <p className="type-caption text-muted uppercase">What was done on site</p>
        <ul className="flex flex-col gap-2">
          {DONE.map(({ photo, text }, i) => (
            <li key={text}>
              <Reveal delay={i * 150}>
                <div className="flex items-center gap-3 rounded-control border border-line p-2">
                  <Image
                    src={photo.src}
                    alt=""
                    width={photo.width}
                    height={photo.height}
                    sizes="64px"
                    className="size-14 shrink-0 rounded-control object-cover"
                  />
                  <span className="min-w-0 flex-1 text-ink">{text}</span>
                  <span className="type-small flex shrink-0 items-center text-accent">
                    View photo
                    <ChevronRight aria-hidden strokeWidth={1.75} className="size-4" />
                  </span>
                </div>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center justify-between gap-3 rounded-control bg-mist p-3">
        <span className="flex flex-col">
          <span className="type-caption text-muted uppercase">Money</span>
          <span className="type-small text-ink">Taken from the payment record, never from the AI</span>
        </span>
        <Lock aria-hidden strokeWidth={1.75} className="size-5 shrink-0 text-slate" />
      </div>

      <div className="mt-auto flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3 rounded-control border border-line p-3">
          <span className="flex flex-col">
            <span className="font-semibold text-ink">Slab milestone · verified</span>
            <span className="type-small text-slate">Waiting for your approval</span>
          </span>
          <span className="flex min-h-11 items-center rounded-control bg-navy-900 px-4 font-semibold text-white">
            Review
          </span>
        </div>
        <figcaption className="type-small text-muted">
          AI drafts and checks — it never approves, releases or pays. Illustration with sample content, not a
          real project.
        </figcaption>
      </div>
    </figure>
  );
}
