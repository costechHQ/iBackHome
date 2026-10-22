"use client";

/**
 * Ends the session on this browser (clears the cookies; MX-19: the backend can't revoke the refresh token yet)
 * and shows the signed-out page. A full page load, not router.push: it drops every cached query of the person
 * who just left.
 */
export async function signOutHere(): Promise<void> {
  await fetch("/api/session/sign-out", { method: "POST" }).catch(() => null);
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/signed-out");
}
