/**
 * DPDP Act 2023 plain-language explainer for patients.
 *
 * Collapsible card. Expanded the first time; the collapsed state is
 * remembered in localStorage so returning users are not cluttered.
 */

import { useState, type ComponentType } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronDown,
  ExternalLink,
  FileCheck2,
  Eye,
  Pencil,
  History,
  Megaphone,
  UserCheck,
  ShieldCheck,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const STORAGE_KEY = "dpdp_explainer_collapsed";
const PANEL_ID = "dpdp-explainer-panel";

type Right = {
  title: string;
  text: string;
  icon: ComponentType<{ className?: string }>;
  link?: { to: string; label: string };
};

// Routes verified in src/App.tsx (patient routes).
const RIGHTS: Right[] = [
  {
    title: "Give or withdraw consent",
    text: "You can say yes or change your mind at any time.",
    icon: FileCheck2,
    link: { to: "/consents", label: "Consent Center" },
  },
  {
    title: "Know what data is held",
    text: "Ask what data is stored about you and how it is used.",
    icon: Eye,
    link: { to: "/my-data", label: "Personal Data Center" },
  },
  {
    title: "Correct or erase your data",
    text: "Fix wrong details, or ask for your data to be deleted.",
    icon: Pencil,
    link: { to: "/my-data", label: "Personal Data Center" },
  },
  {
    title: "See who accessed your records",
    text: "Check a clear history of who looked at your data.",
    icon: History,
    link: { to: "/timeline", label: "Audit Timeline" },
  },
  {
    title: "Raise a grievance",
    text: "Contact the hospital's Data Protection Officer first. If it is not solved, you can go to the Data Protection Board of India.",
    icon: Megaphone,
  },
  {
    title: "Nominate someone",
    text: "Choose a person who can act for you if you die or are unable to.",
    icon: UserCheck,
  },
];

const PROTECTIONS = [
  "Your consent records are secured on a blockchain.",
  "Your personal data is encrypted at rest.",
  "Every access to your data is logged in a tamper-evident audit trail.",
  "A redactable blockchain lets your data be erased while keeping integrity.",
  "Admin accounts are protected with MFA, fingerprint and RFID presence checks.",
];

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function DpdpActExplainer() {
  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      /* storage unavailable: ignore */
    }
  };

  return (
    <Card>
      <h2 className="m-0">
        <button
          type="button"
          onClick={toggle}
          aria-expanded={!collapsed}
          aria-controls={PANEL_ID}
          className="flex w-full items-center gap-3 rounded-xl p-4 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 sm:p-6"
        >
          <BookOpen className="h-5 w-5 shrink-0 text-primary-600" aria-hidden="true" />
          <span className="min-w-0 flex-1 break-words text-base font-semibold text-neutral-800 sm:text-lg">
            Your data, your rights: the DPDP Act 2023
          </span>
          <span className="shrink-0 text-xs font-medium text-neutral-600">
            {collapsed ? "Show" : "Hide"}
          </span>
          <ChevronDown
            className={`h-5 w-5 shrink-0 text-neutral-500 transition-transform ${collapsed ? "" : "rotate-180"}`}
            aria-hidden="true"
          />
        </button>
      </h2>

      <div id={PANEL_ID} hidden={collapsed}>
        <CardContent className="space-y-6 p-4 pt-0 sm:p-6 sm:pt-0">
          <section aria-labelledby="dpdp-what">
            <h3 id="dpdp-what" className="text-sm font-semibold text-neutral-800">
              What is it?
            </h3>
            <p className="mt-1 break-words text-sm text-neutral-700">
              The Digital Personal Data Protection Act, 2023 is India&apos;s law on how
              organisations collect and use your personal data. Hospitals and apps (called
              &quot;Data Fiduciaries&quot;) must ask for your clear consent, use your data only for
              the purpose you agreed to, keep it safe, and delete it when it is no longer needed.
              You are the &quot;Data Principal&quot;: the owner of your data.
            </p>
          </section>

          <section aria-labelledby="dpdp-why">
            <h3 id="dpdp-why" className="text-sm font-semibold text-neutral-800">
              Why it matters for patients
            </h3>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-neutral-700">
              <li className="break-words">Health records are very sensitive.</li>
              <li className="break-words">
                Leaks can cause discrimination, fraud or embarrassment.
              </li>
              <li className="break-words">You decide who sees your records, and why.</li>
            </ul>
          </section>

          <section aria-labelledby="dpdp-rights">
            <h3 id="dpdp-rights" className="text-sm font-semibold text-neutral-800">
              Your rights
            </h3>
            <ul className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {RIGHTS.map(({ title, text, icon: Icon, link }) => (
                <li key={title} className="flex gap-3 rounded-lg border border-neutral-200 p-3">
                  <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary-600" aria-hidden="true" />
                  <div className="min-w-0">
                    <p className="break-words text-sm font-medium text-neutral-800">{title}</p>
                    <p className="mt-0.5 break-words text-xs text-neutral-600">{text}</p>
                    {link && (
                      <Link
                        to={link.to}
                        className="mt-1 inline-block text-xs font-medium text-primary-700 underline hover:text-primary-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                      >
                        {link.label}
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="dpdp-duties">
            <h3 id="dpdp-duties" className="text-sm font-semibold text-neutral-800">
              Your duties
            </h3>
            <p className="mt-1 break-words text-sm text-neutral-700">
              Give true information. Do not file false or frivolous complaints.
            </p>
          </section>

          <section aria-labelledby="dpdp-protect">
            <h3
              id="dpdp-protect"
              className="flex items-center gap-2 text-sm font-semibold text-neutral-800"
            >
              <ShieldCheck className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
              How this platform protects you
            </h3>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-neutral-700">
              {PROTECTIONS.map((p) => (
                <li key={p} className="break-words">
                  {p}
                </li>
              ))}
            </ul>
          </section>

          <p className="break-words border-t border-neutral-200 pt-3 text-xs text-neutral-600">
            Simplified summary for awareness, not legal advice.{" "}
            <a
              href="https://www.meity.gov.in/data-protection-framework"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium text-primary-700 underline hover:text-primary-800"
            >
              Official MeitY DPDP Act page
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
              <span className="sr-only">(opens in a new tab)</span>
            </a>
          </p>
        </CardContent>
      </div>
    </Card>
  );
}
