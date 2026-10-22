// The backend answers every error as {"error": {"code", "message"}}. ApiError carries it; toUiState() maps it
// to the designed pattern (Docs/design/04-api-mapping/error-codes-to-ui.md). Screens show designed copy for
// the pattern, never the raw message, and a 409 is a conflict state, never an error boundary.

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly retryAfterSeconds: number | null = null,
    readonly requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Thrown when the request never reached us (offline, DNS, connection reset). */
export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super("The request didn't reach the server.", { cause });
    this.name = "NetworkError";
  }
}

const HTTP_FALLBACK_CODES: Record<number, string> = {
  400: "bad_request",
  401: "unauthorized",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
  422: "validation_error",
  429: "rate_limited",
};

/**
 * The ApiError for a failed response. Pass `parsed` when the body was already read (openapi-fetch reads it into
 * `error`, so the response body can't be read again); otherwise the body is read here.
 */
export async function apiErrorFrom(response: Response, parsed?: unknown): Promise<ApiError> {
  let code = HTTP_FALLBACK_CODES[response.status] ?? (response.status >= 500 ? "server_error" : "error");
  let message = response.statusText || "Request failed";
  try {
    const body = (parsed !== undefined ? parsed : await response.clone().json()) as {
      error?: { code?: unknown; message?: unknown };
    } | null;
    if (typeof body?.error?.code === "string") code = body.error.code;
    if (typeof body?.error?.message === "string") message = body.error.message;
  } catch {
    // Not JSON (a proxy or gateway page): keep the HTTP fallback.
  }
  const retryAfter = Number(response.headers.get("retry-after"));
  return new ApiError(
    response.status,
    code,
    message,
    Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    response.headers.get("x-request-id"),
  );
}

export type OtpProblem = "invalid_code" | "otp_expired" | "too_many_attempts";

export type UiState =
  | { kind: "offline" }
  | { kind: "session_expired" }
  | { kind: "forbidden"; code: string }
  | { kind: "not_found" }
  | { kind: "conflict"; code: string }
  | { kind: "validation"; code: string }
  | { kind: "otp"; problem: OtpProblem }
  | { kind: "rate_limited"; retryAfterSeconds: number | null }
  | { kind: "channel_unavailable" }
  | { kind: "send_failed" }
  | { kind: "server"; requestId: string | null };

const OTP_PROBLEMS: ReadonlySet<string> = new Set(["invalid_code", "otp_expired", "too_many_attempts"]);

export function toUiState(error: unknown): UiState {
  if (error instanceof NetworkError) return { kind: "offline" };
  if (!(error instanceof ApiError)) return { kind: "server", requestId: null };

  const { status, code } = error;
  // Login codes (the backend's codes; the design assumed others, see PACKAGE-REPORT).
  if (OTP_PROBLEMS.has(code)) return { kind: "otp", problem: code as OtpProblem };
  if (code === "notifications_not_configured") return { kind: "channel_unavailable" };
  if (code === "notification_failed") return { kind: "send_failed" };
  if (status === 429) return { kind: "rate_limited", retryAfterSeconds: error.retryAfterSeconds };

  if (status === 401) return { kind: "session_expired" };
  if (status === 403) return { kind: "forbidden", code };
  if (status === 404) return { kind: "not_found" };
  if (status === 409) return { kind: "conflict", code };
  if (status === 400 || status === 422) return { kind: "validation", code };
  return { kind: "server", requestId: error.requestId };
}
