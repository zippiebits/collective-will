import {ReactNode} from "react";
import {NextIntlClientProvider} from "next-intl";
import {getMessages, getTranslations} from "next-intl/server";
import {Inter} from "next/font/google";

import {Footer} from "@/components/Footer";
import {NavBar} from "@/components/NavBar";
import {auth} from "@/lib/auth";
import "../globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

type Props = {
  children: ReactNode;
  params: Promise<{locale: "fa" | "en"}>;
};

export async function generateMetadata({params}: {params: Promise<{locale: string}>}) {
  const {locale} = await params;
  const t = await getTranslations({locale, namespace: "common"});
  return {
    title: {
      template: `%s | ${t("appTitle")}`,
      default: t("appTitle"),
    },
    description: locale === "fa"
      ? "ایرانیان چه می‌خواهند؟ به ما کمک کنید تا بفهمیم."
      : "What do Iranians want? Help us find out.",
  };
}

export default async function LocaleLayout({children, params}: Props) {
  const {locale} = await params;
  const messages = await getMessages();
  const direction = locale === "fa" ? "rtl" : "ltr";
  const showOpsLink = process.env.OPS_CONSOLE_SHOW_IN_NAV === "true";
  const session = await auth();
  const userEmail = session?.user?.email ?? undefined;

  return (
    <html lang={locale} dir={direction} className={inter.variable}>
      <body className="min-h-screen bg-gray-50 font-sans text-gray-900 antialiased dark:bg-slate-900 dark:text-slate-100">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <NavBar showOpsLink={showOpsLink} userEmail={userEmail} />
          <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
            {children}
          </main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
