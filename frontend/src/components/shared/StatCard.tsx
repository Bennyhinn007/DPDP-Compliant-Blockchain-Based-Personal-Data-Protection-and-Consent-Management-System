/**
 * Statistics Card.
 *
 * Clean metric card: near-black value, muted label, one soft-tinted icon
 * chip. Single accent by default; status colors only carry real meaning.
 * No gradients, high readability.
 */

import { type LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  variant?: "primary" | "success" | "warning" | "secondary" | "danger";
  subtitle?: string;
}

// Soft tinted chip per meaning. primary/secondary share the single accent.
const chipStyles = {
  primary: "bg-primary-50 text-primary-600 ring-primary-100",
  secondary: "bg-primary-50 text-primary-600 ring-primary-100",
  success: "bg-success/10 text-success ring-success/20",
  warning: "bg-warning/10 text-warning ring-warning/20",
  danger: "bg-danger/10 text-danger ring-danger/20",
};

export function StatCard({ label, value, icon: Icon, variant = "primary", subtitle }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="group"
    >
      <Card className="p-5 transition-all duration-300 group-hover:-translate-y-0.5 group-hover:shadow-md">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-neutral-500">{label}</p>
            <p className="mt-2 text-3xl font-bold tracking-tight text-neutral-900">{value}</p>
            {subtitle && <p className="mt-1 text-xs text-neutral-400">{subtitle}</p>}
          </div>
          <div
            className={cn(
              "flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl ring-1 transition-transform duration-300 group-hover:scale-105",
              chipStyles[variant]
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
