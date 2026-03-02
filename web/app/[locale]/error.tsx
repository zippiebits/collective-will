"use client";

import {useTranslations} from "next-intl";

export default function ErrorPage({reset}: {error: Error; reset: () => void}) {
  const t = useTranslations("common");

  return (
    <div className="flex min-h-[50vh] items-center justify-center px-4">
      <div className="text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <svg
            className="h-8 w-8 text-red-600 dark:text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
            />
          </svg>
        </div>
        <h1 className="mt-4 text-xl font-bold">{t("error")}</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-slate-400">
          {t("errorDescription")}
        </p>
        <button
          type="button"
          onClick={reset}
          className="mt-6 rounded-lg bg-accent px-6 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          {t("retry")}
        </button>
      </div>
    </div>
  );
}
