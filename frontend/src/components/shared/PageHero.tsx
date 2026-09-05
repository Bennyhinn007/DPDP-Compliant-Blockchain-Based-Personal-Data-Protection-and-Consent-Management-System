/**
 * Page Hero Banner.
 *
 * Clean white header card: near-black title, muted subtitle, a single
 * accent icon tile, an optional status pill, and an actions slot.
 * No gradients, one accent color — maximum readability.
 */

import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface PageHeroProps {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  /** Small pill shown on the right, e.g. a live status. */
  pill?: { label: string; tone?: "success" | "primary" | "warning" | "danger" | "accent" };
  /** Optional right-aligned actions (buttons, etc.). */
  actions?: ReactNode;
  className?: string;
}

const pillTones = {
  primary: "bg-primary-50 text-primary-700 ring-primary-200",
  accent: "bg-primary-50 text-primary-700 ring-primary-200",
  success: "bg-success/10 text-success ring-success/20",
  warning: "bg-warning/10 text-warning ring-warning/20",
  danger: "bg-danger/10 text-danger ring-danger/20",
};

export function PageHero({ title, subtitle, icon: Icon, pill, actions, className }: PageHeroProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={cn(
        "relative overflow-hidden rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm lg:p-7",
        className
      )}
    >
      {/* Single thin accent bar on the left edge */}
      <div className="absolute inset-y-0 left-0 w-1 bg-primary-500" />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          {Icon && (
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-600 ring-1 ring-primary-100">
              <Icon className="h-6 w-6" />
            </div>
          )}
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-neutral-900">{title}</h1>
              {pill && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1",
                    pillTones[pill.tone ?? "primary"]
                  )}
                >
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-60" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-current" />
                  </span>
                  {pill.label}
                </span>
              )}
            </div>
            {subtitle && <p className="mt-1 text-sm text-neutral-500">{subtitle}</p>}
          </div>
        </div>

        {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
      </div>
    </motion.div>
  );
}
