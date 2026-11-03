# Proposal

## Why

On screens at the `md` breakpoint and wider, a fixed banner (LiveKit logo on the left, "Built with LiveKit Agents" on the right) is shown across the top of every page. It is starter-template branding that this app does not want to display.

## What Changes

- Remove the `<header>` banner from `app/layout.tsx` (logo link and "Built with LiveKit Agents" text).
- Delete `public/lk-logo.svg` and `public/lk-logo-dark.svg`, which nothing else references.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behavior changes; this is a visual branding removal, so the change sets `skip_specs: true`.

## Impact

- Code: `app/layout.tsx` only; two unused assets removed from `public/`.
- No API, dependency, or env var impact.

## Out of Scope

- The page `<title>` and meta description in `app/layout.tsx` (they still mention LiveKit).
- The welcome-view link to the LiveKit docs, the `ThemeToggle`, and `public/lk-wordmark.svg`.
- The `livekit` button variant in the agents-ui control bar.
