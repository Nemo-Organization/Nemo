# Feature template

Copy this folder to start a new feature.

```bash
cp -r src/features/_template src/features/<feature-name>
```

1. Rename files/identifiers: `template` → `<feature-name>`, `Template` → `<FeatureName>`.
2. Add i18n files `src/i18n/messages/{en,vi}/<feature-name>.json`, then run `npm run gen:i18n`.
3. Add the route in `src/config/routes.ts` and the page in `src/app/[locale]/<route>/page.tsx`
   (pages stay thin: they only render the feature's exported view).
4. Replace each `TODO` and delete the mock once a real API exists.

```
<feature-name>/
├─ components/   UI that belongs to this feature
├─ hooks/        React hooks (data + UI logic)
├─ services/     API / server-action calls (no React)
├─ types/        TypeScript types
├─ constants/    Feature constants
├─ mocks/        Mock data (temporary)
└─ index.ts      Public API of the feature
```

Example `en/<feature-name>.json`:

```json
{ "title": "TODO" }
```

> The `_template` folder is type-checked, so it must always compile.
> Delete it from your own fork if you do not need it.
