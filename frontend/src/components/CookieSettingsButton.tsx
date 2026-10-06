"use client";

export function CookieSettingsButton() {
  return <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.dispatchEvent(new Event("pp:cookie-settings"))}>Open cookie settings</button>;
}
