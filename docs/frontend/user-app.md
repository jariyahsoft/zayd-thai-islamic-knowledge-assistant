# User Application Shell

Implementation notes for TASK-09-01 in `apps/web`.

## Architecture

| Area | Location |
|---|---|
| Shared shell primitives | `packages/ui` (`UserAppShell`, `ArabicText`, manifest helpers) |
| App composition | `apps/web/app` |
| Global styling | `apps/web/app/globals.css` |
| PWA manifest | `apps/web/app/manifest.ts` + `public/icons` |

## Mobile-first Navigation

The shell uses a sticky bottom navigation bar with four destinations:

- `/` — หน้าแรก
- `/chat` — ถาม
- `/history` — ประวัติ
- `/settings` — ตั้งค่า

The layout caps content width for larger screens while preserving touch-friendly targets on phones.

## Typography and RTL

- Thai body text uses a Thai-first font stack (`Sarabun`, `Noto Sans Thai`, `IBM Plex Sans Thai`).
- Arabic snippets are rendered through `ArabicText`, which sets `dir="rtl"`, `lang="ar"`, and `unicode-bidi: isolate` so Arabic passages do not reverse surrounding Thai layout.
- Long strings use `overflow-wrap: anywhere` to prevent horizontal overflow on narrow screens.

## Theme Support

`UserAppClient` stores theme mode in client state and writes `data-theme` on `document.documentElement`. CSS variables in `globals.css` switch between light and dark palettes.

## PWA

- Manifest is generated from `createUserAppManifest()` in `@zayd/ui`.
- `display: standalone`, Thai `lang`, relative `start_url`, and SVG icons are required for installability checks.
- `layout.tsx` sets viewport theme colors and Apple web-app metadata.

## Security Notes

- The shell does not render API secrets or hidden model traces.
- Placeholder screens avoid religious rulings; production copy requires human content review.
- Arabic and Thai demo strings are limited to neutral examples.

## Follow-up Tasks

- TASK-09-02 wires `/chat` to the SSE streaming API.
- TASK-09-04 adds preference controls under `/settings`.
- TASK-09-05 populates `/history`.