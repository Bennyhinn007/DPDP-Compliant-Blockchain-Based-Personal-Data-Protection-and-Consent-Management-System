import { describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";

vi.mock("@/services/api", () => {
  throw new Error("The walkthrough must not import the API client");
});

import { PatientWalkthrough } from "./PatientWalkthrough";

describe("PatientWalkthrough", () => {
  it("renders the synthetic example without network or storage access", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("no network"));
    const storageSpy = vi.fn();
    const storage = { getItem: storageSpy, setItem: storageSpy, removeItem: storageSpy };
    vi.stubGlobal("localStorage", storage);

    const html = renderToString(
      <StaticRouter location="/walkthrough">
        <PatientWalkthrough />
      </StaticRouter>,
    );

    expect(html).toContain("Synthetic patient");
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(storageSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
    fetchSpy.mockRestore();
  });
});
