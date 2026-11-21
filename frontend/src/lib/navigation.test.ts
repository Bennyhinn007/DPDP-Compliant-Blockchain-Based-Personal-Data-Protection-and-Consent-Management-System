import { describe, expect, it } from "vitest";
import { portalPath } from "./navigation";

describe("portalPath", () => {
  it("routes each role to its portal", () => {
    expect(portalPath("admin")).toBe("/dpo");
    expect(portalPath("dpo")).toBe("/dpo");
    expect(portalPath("doctor")).toBe("/doctor");
    expect(portalPath("registration_staff")).toBe("/staff/register-patient");
    expect(portalPath("patient")).toBe("/dashboard");
    expect(portalPath("unknown")).toBe("/unauthorized");
  });

  it("keeps a patient's own destination", () => {
    expect(portalPath("patient", "/consents")).toBe("/consents");
    expect(portalPath("patient", "/profile")).toBe("/profile");
  });

  it("sends a patient to the dashboard for a foreign destination", () => {
    expect(portalPath("patient", "/doctor")).toBe("/dashboard");
    expect(portalPath("patient", "/unauthorized")).toBe("/dashboard");
    expect(portalPath("patient", "/dpo/compliance")).toBe("/dashboard");
  });
});
