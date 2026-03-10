import {getTranslations, getLocale} from "next-intl/server";
import Link from "next/link";

import {PageShell} from "@/components/ui/PageShell";

type FaqItem = {
  question: string;
  answer: string;
};

type FaqSection = {
  title: string;
  items: FaqItem[];
};

export async function generateMetadata() {
  const t = await getTranslations("faq");
  return {title: t("pageTitle")};
}

export default async function FaqPage() {
  const t = await getTranslations("faq");
  const nav = await getTranslations("nav");
  const locale = await getLocale();

  const sections: FaqSection[] = [
    {
      title: t("safetyTitle"),
      items: [
        {question: t("safetyQ1"), answer: t("safetyA1")},
        {question: t("safetyQ2"), answer: t("safetyA2")},
        {question: t("safetyQ3"), answer: t("safetyA3")},
        {question: t("safetyQ4"), answer: t("safetyA4")},
        {question: t("safetyQ5"), answer: t("safetyA5")},
        {question: t("safetyQ6"), answer: t("safetyA6")},
      ],
    },
    {
      title: t("howItWorksTitle"),
      items: [
        {question: t("howQ1"), answer: t("howA1")},
        {question: t("howQ2"), answer: t("howA2")},
        {question: t("howQ3"), answer: t("howA3")},
        {question: t("howQ4"), answer: t("howA4")},
        {question: t("howQ5"), answer: t("howA5")},
      ],
    },
    {
      title: t("aboutTitle"),
      items: [
        {question: t("aboutQ1"), answer: t("aboutA1")},
        {question: t("aboutQ2"), answer: t("aboutA2")},
        {question: t("aboutQ3"), answer: t("aboutA3")},
        {question: t("aboutQ4"), answer: t("aboutA4")},
        {question: t("aboutQ5"), answer: t("aboutA5")},
      ],
    },
  ];

  return (
    <PageShell title={t("pageTitle")} subtitle={t("pageSubtitle")}>
      <div className="space-y-10">
        {sections.map((section) => (
          <section key={section.title}>
            <h2 className="mb-4 text-lg font-bold text-gray-900 dark:text-white">
              {section.title}
            </h2>
            <div className="space-y-4">
              {section.items.map((item) => (
                <div
                  key={item.question}
                  className="rounded-lg border border-gray-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800"
                >
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                    {item.question}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600 dark:text-slate-400">
                    {item.answer}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ))}

        <div className="rounded-lg border border-accent/20 bg-accent/5 p-5 text-center dark:border-accent/30 dark:bg-accent/10">
          <p className="text-sm text-gray-700 dark:text-slate-300">
            {t("auditCta")}
          </p>
          <Link
            href={`/${locale}/collective-concerns/evidence`}
            className="mt-2 inline-block text-sm font-semibold text-accent hover:underline"
          >
            {nav("audit")} →
          </Link>
        </div>
      </div>
    </PageShell>
  );
}
