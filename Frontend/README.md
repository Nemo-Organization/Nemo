# Nemo — Frontend

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · shadcn/ui (Base UI, `base-lyra` style, Phosphor icons) · next-intl · Redux Toolkit · TanStack Table v9 · Recharts.

> Read [AGENTS.md](./AGENTS.md) before writing code: this Next.js 16 version introduces breaking changes compared to earlier releases. Canonical documentation is bundled locally in `node_modules/next/dist/docs/`.

## Prerequisites

- Node.js 20+
- npm

## Getting Started

```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000 (automatically runs gen:i18n)
```

## Environment Variables

Copy `.env.example` to `.env.local` and configure the values (never commit real secrets):

| Variable | Description | Default / Example |
| --- | --- | --- |
| `NEXT_PUBLIC_APP_URL` | Public base URL of the app (metadata, absolute links) | `http://localhost:3000` |
| `API_BASE_URL` | Backend API base URL *(planned — uncomment when backend is ready)* | — |

## Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Run the development server (runs `predev` → `gen:i18n` first) |
| `npm run build` | Build for production (runs `prebuild` → `gen:i18n:strict` first) |
| `npm run start` | Start the production server |
| `npm run lint` | Run ESLint (`eslint-config-next` core-web-vitals + TypeScript) |
| `npm run typecheck` | Run TypeScript type checking (`tsc --noEmit`) |
| `npm run gen:i18n` | Generate `src/i18n/namespaces.generated.ts` from `src/i18n/messages/en/*.json` and warn on key mismatches |
| `npm run gen:i18n:strict` | Same as `gen:i18n`, but exits with an error if any locale has missing/extra files or keys compared to `en` |

## Project Structure

```text
scripts/
└─ generate-namespaces.mjs   Generates i18n namespace types and validates locale parity

src/
├─ proxy.ts                  next-intl locale routing proxy (Next.js 16)
├─ app/
│  ├─ globals.css            Tailwind CSS 4 entry, custom @theme type scale, theme tokens
│  └─ [locale]/              Thin App Router pages: compose features, metadata, error/loading/not-found
├─ features/                 Domain modules (components, hooks, services, types, constants, mocks, index.ts)
│  ├─ dashboard/             Overview metrics, activity chart, usage card, quick links, recent leads
│  ├─ leads/                 Leads data table, toolbar, faceted filters, row actions
│  └─ _template/             Starter template for new features (type-checked; see its README)
├─ components/
│  ├─ ui/                    shadcn/ui primitives — DO NOT edit manually (CLI overwrites)
│  ├─ layout/                Shared page chrome (page-breadcrumbs, page-header, page-container)
│  ├─ data-table/            Reusable TanStack Table v9 wrapper, pagination, sorting, faceted filters
│  └─ shared/                Cross-feature shared components
├─ config/                   App-wide configuration (`routes.ts`, `fonts.ts`)
├─ hooks/                    Shared React hooks (`use-mobile.ts`)
├─ i18n/                     next-intl setup (`routing.ts`, `request.ts`, `navigation.ts`, `messages/{en,vi}/`)
├─ lib/                      Pure utility helpers (`utils.ts`)
├─ store/                    Redux Toolkit store, typed hooks, provider, and slices (`ui-slice.ts`)
└─ styles/overrides/         Per-component shadcn/ui CSS overrides (`tokens`, `base`, `card`, `table`, `chart`, `input`, `overlay`, `progress`)
```

## Architecture & Conventions

- **Next.js 16 Config**: Turbopack CSS loader (`@tailwindcss/turbopack`), React Compiler (`reactCompiler: true`), `cacheComponents: true`, and `partialPrefetching: true` are enabled in `next.config.ts`.
- **Naming**:
  - Files: `kebab-case`
  - Components: `PascalCase`
  - Hooks: `useXxx` in `use-xxx.ts`
  - Feature modules: `*.types.ts`, `*.service.ts`, `*.mock.ts`, `*.constants.ts`
- **Feature Boundaries**: Import across features only through their public barrel (`@/features/<name>`), never from internal paths.
- **Thin Routes**: Keep files in `src/app/[locale]/` thin — delegate UI and domain logic to feature views.
- **Styling & Theming**:
  - Use Tailwind and shadcn semantic tokens (`bg-background`, `text-foreground`, `border`, etc.).
  - The custom design tokens (Teal primary palette, sharp `0rem` corner radius) live in `src/styles/overrides/tokens.css`, and the shared type scale (one step above Tailwind defaults) lives under `@theme` in `src/app/globals.css`.
  - Never edit `src/components/ui/*` directly. Add overrides in `src/styles/overrides/<component>.css` and import them in `src/styles/overrides/index.css`.
- **Typography**: `Inter Tight` (`latin`, `vietnamese`) loaded via `next/font/google` in `src/config/fonts.ts` and bound to `--font-inter-tight`.
- **Internationalization (`next-intl`)**:
  - Supported locales: `vi` (default) and `en` (configured in `src/i18n/routing.ts`).
  - Do not hardcode user-facing copy. Create one namespace per feature in `src/i18n/messages/{en,vi}/<feature>.json`, then run `npm run gen:i18n`.
- **Routing**: Define route paths in `src/config/routes.ts` and use `Link`, `useRouter`, `usePathname`, and `redirect` from `@/i18n/navigation`.
- **Data Tables**: Reuse components and the shared `dataTableFeatures` preset from `src/components/data-table/`.
- **Data & Mocks**: Features currently read mock data from `src/features/*/mocks/`. Replace with real API calls in `services/` once the backend is available, then remove the mock files.

## Adding a New Feature

Follow the step-by-step guide in [src/features/_template/README.md](./src/features/_template/README.md).

## Recommended Additions (Not Yet Configured)

- Code formatting: Prettier + `prettier-plugin-tailwindcss`
- Git hooks: Husky + `lint-staged`
- Testing: Vitest + React Testing Library (unit/component), Playwright (E2E)
- Runtime validation: `zod` (environment variables & forms)
- CI/CD: GitHub Actions (`lint`, `typecheck`, `build`)
- Observability: Sentry / structured logging
