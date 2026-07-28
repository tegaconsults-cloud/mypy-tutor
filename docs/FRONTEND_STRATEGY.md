# Frontend strategy

## Canonical frontend

The active frontend for the product is the React/Vite app in [frontend-react](../frontend-react).

## Why this is the primary target

- It is the most recent implementation.
- It has a modern component structure and TypeScript support.
- It is the best place for new UI work, bug fixes, and feature development.

## Legacy frontend folders

- [frontend](../frontend) contains older static assets and should be treated as legacy/reference material.
- [static](../static) contains static files that may be used for hosting or marketing pages, but are not the main app shell.

## Recommendation

For new features, styling changes, and bug fixes, work in [frontend-react](../frontend-react) first. Keep the legacy folders updated only when required for compatibility or deployment reasons.
