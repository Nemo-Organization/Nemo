# My App

Next.js 16 (App Router) · React 19 · Tailwind CSS 4 · shadcn/ui (Base UI, style `base-lyra`) · next-intl · Redux Toolkit · TanStack Table v9.

> Đọc [AGENTS.md](./AGENTS.md) trước khi viết code: Next.js ở đây có breaking changes so với kiến thức cũ,
> tài liệu chuẩn nằm ở `node_modules/next/dist/docs/`.

## Bắt đầu

```bash
npm install
cp .env.example .env.local
npm run dev        # http://localhost:3000 (tự chạy gen:i18n)
```

| Script | Mục đích |
| --- | --- |
| `npm run dev` / `build` / `start` | Chạy dev / build / chạy production |
| `npm run lint` | ESLint |
| `npm run typecheck` | Kiểm tra TypeScript |
| `npm run gen:i18n` | Sinh `src/i18n/namespaces.generated.ts` từ `messages/en/*.json` |
| `npm run gen:i18n:strict` | Như trên nhưng lỗi nếu `vi` thiếu/dư key so với `en` (chạy trước `build`) |

## Cấu trúc thư mục

```
src/
├─ app/[locale]/        Route (mỏng): chỉ ghép feature, metadata, error/loading/not-found
├─ features/<name>/     Mỗi tính năng: components, hooks, services, types, constants, mocks, index.ts
│  └─ _template/        Mẫu để copy khi tạo feature mới (xem README trong thư mục)
├─ components/
│  ├─ ui/               shadcn/ui — KHÔNG sửa tay (CLI sẽ ghi đè)
│  ├─ layout/           Khung trang dùng chung (breadcrumbs, header, container)
│  └─ data-table/       Bảng dữ liệu dùng chung (TanStack Table v9)
├─ config/              Hằng cấu hình: routes, fonts
├─ hooks/               Hook dùng chung
├─ i18n/                next-intl: routing, request, messages/{en,vi}/<namespace>.json
├─ lib/                 Tiện ích thuần (utils)
├─ store/               Redux store + slices
└─ styles/overrides/    Ghi đè style của shadcn/ui tách riêng theo từng thành phần (tokens, card, table, chart...)
```

## Quy ước

- **Tên file**: `kebab-case`; component `PascalCase`; hook `useXxx` trong `use-xxx.ts`;
  mock `*.mock.ts`, type `*.types.ts`, service `*.service.ts`.
- **Import giữa feature** chỉ qua `@/features/<name>` (barrel `index.ts`).
- **Style**: dùng token Tailwind/shadcn (`bg-background`, `border`, ...). Muốn ghi đè shadcn thì thêm vào
  `src/styles/overrides/<component>.css` (và import vào `index.css`), không sửa `components/ui/*`. Thang cỡ chữ dùng chung nằm ở `@theme` trong `globals.css`.
- **Font**: Inter Tight qua `next/font` (`src/config/fonts.ts`).
- **i18n**: không hard-code text. Mỗi feature một namespace (`<feature>.json`) ở cả `en` và `vi`,
  sau đó chạy `npm run gen:i18n`.
- **Route**: khai báo trong `src/config/routes.ts`, dùng `Link` từ `@/i18n/navigation`.
- **Dữ liệu**: hiện là mock trong `features/*/mocks`. Thay bằng service thật rồi xóa mock.

## Thêm feature mới

Xem [src/features/_template/README.md](./src/features/_template/README.md).

## Việc nên bổ sung (chưa có trong repo)

Prettier + `prettier-plugin-tailwindcss`, Husky + lint-staged, kiểm thử (Vitest + Testing Library, Playwright),
validate env/form (zod), CI (GitHub Actions: lint, typecheck, build), Sentry/logging.
