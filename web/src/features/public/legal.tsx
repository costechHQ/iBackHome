import { readFile } from "node:fs/promises";
import path from "node:path";

import Link from "next/link";

import { Alert } from "@/common/ui/alert";
import { Markdown } from "@/common/ui/markdown";

import { PageHero, Section } from "./blocks";

// WEB-PUBLIC-008 Privacy policy and WEB-PUBLIC-009 Terms of use. The legal text is written by the company's
// lawyers, not by us, so each page renders web/content/legal/<name>.md when it exists and otherwise says the
// document is being finalised (PACKAGE-REPORT W-37). The pages are static: the file is read at build time.

export type LegalDoc = "privacy" | "terms";

export const LEGAL_TITLES: Record<LegalDoc, string> = { privacy: "Privacy policy", terms: "Terms of use" };

/** The document's Markdown, or null while it hasn't been supplied (a missing or blank file). */
export async function readLegal(doc: LegalDoc, root = process.cwd()): Promise<string | null> {
  try {
    const text = await readFile(path.join(root, "content", "legal", `${doc}.md`), "utf8");
    return text.trim() ? text : null;
  } catch {
    return null;
  }
}

export async function LegalPage({ doc }: { doc: LegalDoc }) {
  const source = await readLegal(doc);
  const title = LEGAL_TITLES[doc];
  return (
    <>
      <PageHero
        eyebrow="Legal"
        title={title}
        lead={
          doc === "privacy"
            ? "How iBackHome collects, uses and protects personal data, under the Nigeria Data Protection Act 2023."
            : "The agreement between you and iBackHome when you use the service."
        }
      />
      <Section tone="mist" labelledBy="legal-text" className="max-w-3xl">
        <h2 id="legal-text" className="sr-only">
          {title}
        </h2>
        {source ? (
          <div className="rounded-card border border-line bg-white p-6">
            <Markdown source={source} />
          </div>
        ) : (
          <Alert tone="info" title="This document is being finalised">
            The full {title.toLowerCase()} will be published here before launch. Questions in the meantime?{" "}
            <Link href="/contact" className="text-accent underline">
              Contact us
            </Link>
            .
          </Alert>
        )}
      </Section>
    </>
  );
}
