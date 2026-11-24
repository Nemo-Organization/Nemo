import { Suspense } from 'react';
import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getTranslations } from 'next-intl/server';

import { ThemeSync } from '@/components/shared/theme-sync';
import { Toaster } from '@/components/ui/sonner';
import { fontSans } from '@/config/fonts';
import { routing } from '@/i18n/routing';
import StoreProvider from '@/store/store-provider';
import '../globals.css';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('common');

  return {
    title: {
      default: t('app.name'),
      template: `%s | ${t('app.name')}`,
    },
    description: t('app.description'),
  };
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  return (
    // suppressHydrationWarning: ThemeSync toggles .dark before hydration.
    <html lang={locale} className={fontSans.variable} suppressHydrationWarning>
      <head>
        <ThemeSync />
      </head>
      <body className="font-sans antialiased">
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
        <NextIntlClientProvider>
          <ThemeSync />
          <Suspense fallback={null}>
            <StoreProvider>{children}</StoreProvider>
            <Toaster />
          </Suspense>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}