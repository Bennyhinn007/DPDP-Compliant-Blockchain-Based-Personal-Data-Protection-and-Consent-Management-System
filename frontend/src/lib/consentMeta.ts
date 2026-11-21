/**
 * Consent type metadata for display.
 */

import type { ConsentType, ConsentStatus } from "@/types";

export const CONSENT_LABELS: Record<ConsentType, string> = {
  healthcare_treatment: "Healthcare Treatment",
  pharmacy_access: "Pharmacy Access",
  research_access: "Research Access",
  insurance_access: "Insurance Access",
  analytics_access: "Analytics Access",
  marketing_access: "Marketing Access",
};

export const CONSENT_ICONS: Record<ConsentType, string> = {
  healthcare_treatment: "🏥",
  pharmacy_access: "💊",
  research_access: "🔬",
  insurance_access: "📋",
  analytics_access: "📊",
  marketing_access: "📣",
};

export const ALL_CONSENT_TYPES: ConsentType[] = [
  "healthcare_treatment",
  "pharmacy_access",
  "research_access",
  "insurance_access",
  "analytics_access",
  "marketing_access",
];

export function needsRegrant(c: {
  consent_type: string;
  status: string;
  processing_entity_id?: string | null;
}): boolean {
  return c.consent_type === "healthcare_treatment" && c.status === "active" && !c.processing_entity_id;
}

export function statusVariant(status: ConsentStatus): "success" | "danger" | "warning" | "neutral" {
  switch (status) {
    case "active":
      return "success";
    case "withdrawn":
      return "danger";
    case "expired":
      return "warning";
    default:
      return "neutral";
  }
}
