import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, ClipboardList, LockKeyhole, RotateCcw } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import sample from "./consentExample.json";

const stages = [
  { label: "Before consent", consent: "No consent granted", action: "See what granting consent changes" },
  { label: "Medical history shared", consent: "Share medical history", action: "Switch to allergies only" },
  { label: "Allergies only", consent: "Share the allergy list only", action: "See what withdrawal changes" },
  { label: "Consent withdrawn", consent: "Treatment consent withdrawn", action: "Replay the case" },
];

export function PatientWalkthrough() {
  const [step, setStep] = useState(0);
  const stage = stages[step];
  const access = sample.access[step];
  const granted = access.decision === "granted";
  const last = step === stages.length - 1;

  return (
    <div className="min-h-screen bg-[#f5f6f2] text-[#182e2b]">
      <header className="border-b border-[#cdd8d1]">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-10">
          <div className="flex items-center gap-3 font-semibold">
            <img src="/logo-256.png" alt="" width="36" height="36" />
            DPDP Healthcare
          </div>
          <Link className={buttonVariants({ variant: "outline", size: "sm" })} to="/login">
            Sign in to the portal <ArrowRight size={15} />
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-9 sm:px-10 sm:py-14">
        <p className="text-sm font-semibold text-[#356452]">Interactive walkthrough · Synthetic patient</p>
        <h1 className="my-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
          Who can read Mira’s chart?
        </h1>
        <p className="max-w-2xl text-base leading-7 text-[#4f645b]">
          {sample.doctor} has recorded a consultation. Follow four requests to open the same chart
          as {sample.patient} grants, changes and withdraws permission.
        </p>

        <div className="mt-8 grid overflow-hidden rounded-2xl border border-[#c8d4cb] bg-white md:grid-cols-[0.85fr_1.5fr]">
          <nav aria-label="Case stages" className="bg-[#173b34] p-5 text-white sm:p-8">
            <h2 className="mb-4 text-sm font-semibold text-[#c4dacd]">Patient consent</h2>
            <ol className="space-y-2">
              {stages.map((item, index) => (
                <li key={item.label}>
                  <button type="button" aria-current={index === step ? "step" : undefined}
                    onClick={() => setStep(index)}
                    className={`flex w-full items-center justify-between gap-2 rounded-lg border px-4 py-3 text-left text-sm font-semibold focus-visible:outline-white ${index === step
                      ? "border-[#c2e4c9] bg-[#d2ebd6] text-[#163c30]" : "border-white/20 text-white hover:bg-white/10"}`}>
                    {item.label}
                    {index === step && <ArrowRight size={16} aria-hidden="true" />}
                  </button>
                </li>
              ))}
            </ol>
          </nav>
          <section aria-live="polite" aria-atomic="true" className="p-6 sm:p-8">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-[#54665f]">Doctor’s record request</span>
              <span className="font-mono text-xs text-[#54665f]">HTTP {access.status}</span>
            </div>
            <h2 className="my-5 flex items-center gap-3 text-3xl font-semibold">
              {granted ? <Check aria-hidden="true" /> : <LockKeyhole aria-hidden="true" />}
              {granted ? "Access granted" : "Access denied"}
            </h2>
            <dl className="divide-y divide-[#dae2db] border-y border-[#dae2db] text-sm">
              {[
                ["Patient decision", stage.consent],
                ["Consultation returned", access.records ? sample.record : "No consultation returned"],
                ...(access.allergies.length ? [["Allergies returned", access.allergies.join(", ")]] : []),
                ["Requested by", sample.doctor],
              ].map(([label, value]) => (
                <div key={label} className="flex flex-wrap justify-between gap-2 py-3">
                  <dt className="text-[#52655b]">{label}</dt><dd className="font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            <Button className="mt-6 h-auto min-h-10 whitespace-normal bg-[#245448] py-2 hover:bg-[#183f35]"
              onClick={() => setStep(last ? 0 : step + 1)}>
              {stage.action} {last ? <RotateCcw size={15} /> : <ArrowRight size={15} />}
            </Button>
          </section>
        </div>

        <section aria-label="Patient audit history" className="mt-8">
          <h2 className="flex items-center gap-2 text-xl font-semibold">
            <ClipboardList size={20} aria-hidden="true" /> Mira’s audit history
          </h2>
          <ol className="mt-3 divide-y divide-[#d1dbd3] border-y border-[#d1dbd3]">
            {sample.access.slice(0, step + 1).map((attempt, index) => (
              <li key={stages[index].label} className="grid gap-1 py-3 text-sm sm:grid-cols-[12rem_1fr]">
                <strong>{stages[index].label}</strong>
                <span>{attempt.decision === "denied" ? "Record request denied" : attempt.records ? "Medical history shared" : "Allergy list shared"}</span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs leading-5 text-[#52655b]">
            This example replays outcomes checked against the application API. Sign in to work with live records.
          </p>
        </section>
      </main>
    </div>
  );
}
