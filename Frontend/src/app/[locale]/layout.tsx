import { Suspense } from 'react';
import Script from 'next/script';
import { NextIntlClientProvider } from 'next-intl';
import { routing } from '@/i18n/routing';
import StoreProvider from '@/store/store-provider';
import '../globals.css';
import { Toaster } from '@/components/ui/sonner';
import { ThemeSync } from '@/components/shared/theme-sync';
import { fontSans } from '@/config/fonts';
import { THEME_INIT_SCRIPT } from '@/lib/theme';
import { getLocale } from 'next-intl/server';
import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';

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
    // suppressHydrationWarning: the init script adds `dark` to <html> before hydration.
    <html lang={locale} className={fontSans.variable} suppressHydrationWarning>
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