import { describe, expect, it } from "vitest";
import { needsRegrant } from "./consentMeta";

describe("needsRegrant", () => {
  const base = { consent_type: "healthcare_treatment", status: "active", processing_entity_id: null };

  it("flags an active unlinked treatment grant", () => {
    expect(needsRegrant(base)).toBe(true);
    expect(needsRegrant({ ...base, processing_entity_id: undefined })).toBe(true);
  });

  it("ignores linked, inactive and other-purpose grants", () => {
    expect(needsRegrant({ ...base, processing_entity_id: "hospital:citycare" })).toBe(false);
    expect(needsRegrant({ ...base, status: "withdrawn" })).toBe(false);
    expect(needsRegrant({ ...base, status: "expired" })).toBe(false);
    expect(needsRegrant({ ...base, consent_type: "research_access" })).toBe(false);
  });
});
