import { ApiError, NetworkError } from "@/common/api/errors";
import type { components } from "@/common/api/schema";

// The client's side of contractor matching (ADR 0007, phase 2): the brief, its checks (the backend repeats them
// and decides), and what to say when it refuses. The budget isn't asked: it comes from the project.

export type MatchBrief = components["schemas"]["MatchRequestIn"];
export type WorkType = MatchBrief["work_type"];

export const WORK_TYPES: readonly { value: WorkType; label: string }[] = [
  { value: "buildings", label: "Buildings" },
  { value: "roofing", label: "Roofing" },
  { value: "finishing", label: "Finishing" },
  { value: "civil_works", label: "Civil works" },
  { value: "other", label: "Other" },
];

export function workTypeLabel(code: string): string {
  return WORK_TYPES.find((w) => w.value === code)?.label ?? code;
}

export type BriefValues = {
  state: string;
  city: string;
  workType: "" | WorkType;
  timeline: string;
  notes: string;
};

export const EMPTY_BRIEF: BriefValues = { state: "", city: "", workType: "", timeline: "", notes: "" };

export const NOTES_MAX = 2000;

export type BriefField = "state" | "city" | "workType" | "timeline" | "notes";

export function validateBrief(v: BriefValues): Partial<Record<BriefField, string>> {
  const problems: Partial<Record<BriefField, string>> = {};
  if (!v.state) problems.state = "Choose the state you are building in.";
  if (v.city.trim().length < 2) problems.city = "Enter the city or town.";
  if (!v.workType) problems.workType = "Choose the kind of work.";
  if (v.timeline.trim().length < 2) problems.timeline = "Tell us roughly when you want to start.";
  if (v.notes.length > NOTES_MAX) problems.notes = `Keep the notes under ${NOTES_MAX} characters.`;
  return problems;
}

export function toBrief(v: BriefValues): MatchBrief {
  return {
    state: v.state,
    city: v.city.trim(),
    work_type: v.workType as WorkType,
    timeline: v.timeline.trim(),
    notes: v.notes.trim() === "" ? null : v.notes.trim(),
  };
}

export type MatchStatus = "open" | "shortlisted" | "matched" | "cancelled";

/** What the status means to the client, in plain words. */
export const STATUS_COPY: Record<MatchStatus, { label: string; tone: "warn" | "ok" | "neutral" | "bad" }> = {
  open: { label: "We are finding contractors", tone: "warn" },
  shortlisted: { label: "Your shortlist is ready", tone: "ok" },
  matched: { label: "Contractor chosen", tone: "ok" },
  cancelled: { label: "Request cancelled", tone: "neutral" },
};

/** What to tell the person when a write was refused. Never shows a raw backend message. */
export function describeMatchError(error: unknown): string {
  if (error instanceof NetworkError) return "You seem to be offline. Nothing was changed.";
  if (error instanceof ApiError) {
    switch (error.code) {
      case "match_request_exists":
        return "This project already has a contractor request. Reload the page.";
      case "project_not_draft":
        return "The project has moved past set-up, so a contractor can't be requested any more.";
      case "project_has_contractor":
        return "This project already has a contractor.";
      case "contractor_not_available":
        return "That contractor is no longer available. Our team will update your shortlist.";
      case "contractor_not_on_shortlist":
        return "Choose one of the contractors on your shortlist.";
      case "invalid_transition":
        return "This request has changed. Reload the page to see where it is now.";
      case "not_project_member":
      case "match_request_not_found":
        return "We couldn't find that request.";
    }
    if (error.status === 429) return "Too many tries. Wait a moment and try again.";
  }
  return "Something went wrong and nothing was changed. Please try again.";
}
