import Link from "next/link";
import {getLocale, getTranslations} from "next-intl/server";

export default async function NotFound() {
  const t = await getTranslations("common");
  const locale = await getLocale();

  return (
    <div className="flex min-h-[50vh] items-center justify-center px-4">
      <div className="text-center">
        <p className="text-6xl font-bold text-gray-200 dark:text-slate-700">404</p>
        <h1 className="mt-4 text-xl font-bold">{t("pageNotFound")}</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-slate-400">
          {t("pageNotFoundDescription")}
        </p>
        <Link
          href={`/${locale}`}
          className="mt-6 inline-block rounded-lg bg-accent px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          {t("backToHome")}
        </Link>
      </div>
    </div>
  );
}
