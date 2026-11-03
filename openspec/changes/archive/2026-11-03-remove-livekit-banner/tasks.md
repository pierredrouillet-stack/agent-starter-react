# Tasks

## 1. Remove the banner

- [x] 1.1 Delete the `<header>` block (logo link and "Built with LiveKit Agents" text) from `app/layout.tsx`; verify `grep -n "<header" app/layout.tsx` finds nothing and `pnpm lint` passes
- [x] 1.2 Delete `public/lk-logo.svg` and `public/lk-logo-dark.svg`; verify `grep -rn "lk-logo" app components` finds nothing and `pnpm build` succeeds

## 2. Integration check

- [x] 2.1 Run `pnpm format:check`, then load the app at a width of 1280px or more and verify no banner shows on the welcome view, the session view, or `/history`, and the theme toggle still works
