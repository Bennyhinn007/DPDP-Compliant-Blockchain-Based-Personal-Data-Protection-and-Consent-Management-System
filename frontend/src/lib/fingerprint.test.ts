import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  FingerprintError,
  NETWORK_ERROR_MESSAGE,
  getProvider,
  secugenProvider,
} from "./fingerprint";

const fetchMock = vi.fn();

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as unknown as Response;
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("secugenProvider.capture", () => {
  it("posts the expected form and returns template/quality/preview", async () => {
    fetchMock.mockResolvedValue(
      ok({ ErrorCode: 0, TemplateBase64: "TPL", ImageQuality: 77, BMPBase64: "BMP" })
    );
    const res = await secugenProvider.capture();
    expect(res).toEqual({ template: "TPL", quality: 77, previewBmpBase64: "BMP" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://localhost:8443/SGIFPCapture");
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
    const body = (init.body as URLSearchParams).toString();
    expect(body).toContain("Timeout=10000");
    expect(body).toContain("Quality=50");
    expect(body).toContain("templateFormat=ISO");
    expect(body).toContain("imageWSQRate=0.75");
    expect(body).toContain("licstr=");
  });

  it.each([
    [54, "Fingerprint capture timed out. Place your finger on the reader and try again."],
    [55, "SecuGen reader not found. Check that the reader is plugged in."],
    [10004, "SecuGen service access/license error. Check the SecuGen WebAPI license."],
    [10001, "SecuGen license problem. Check VITE_SECUGEN_LICSTR / WebAPI license."],
    [10002, "SecuGen license problem. Check VITE_SECUGEN_LICSTR / WebAPI license."],
    [10003, "SecuGen license problem. Check VITE_SECUGEN_LICSTR / WebAPI license."],
  ])("maps error code %i", async (code, message) => {
    fetchMock.mockResolvedValue(ok({ ErrorCode: code }));
    await expect(secugenProvider.capture()).rejects.toMatchObject({ message, code });
  });

  it("includes the number for unknown codes", async () => {
    fetchMock.mockResolvedValue(ok({ ErrorCode: 999 }));
    await expect(secugenProvider.capture()).rejects.toThrow("SecuGen error (code 999).");
  });

  it("maps a network failure to the install message", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(secugenProvider.capture()).rejects.toThrow(NETWORK_ERROR_MESSAGE);
    expect(NETWORK_ERROR_MESSAGE).toBe(
      "SecuGen service not reachable. Install SecuGen WebAPI and open https://localhost:8443 once to accept the certificate."
    );
  });

  it("maps a non-OK HTTP status to the install message", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    await expect(secugenProvider.capture()).rejects.toBeInstanceOf(FingerprintError);
    await expect(secugenProvider.capture()).rejects.toThrow(NETWORK_ERROR_MESSAGE);
  });

  it("fails when the template is empty", async () => {
    fetchMock.mockResolvedValue(ok({ ErrorCode: 0, TemplateBase64: "" }));
    await expect(secugenProvider.capture()).rejects.toBeInstanceOf(FingerprintError);
  });
});

describe("secugenProvider.match", () => {
  it("returns the matching score", async () => {
    fetchMock.mockResolvedValue(ok({ ErrorCode: 0, MatchingScore: 123 }));
    expect(await secugenProvider.match("A", "B")).toBe(123);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://localhost:8443/SGIMatchScore");
    const body = (init.body as URLSearchParams).toString();
    expect(body).toContain("Template1=A");
    expect(body).toContain("Template2=B");
  });

  it("maps error codes", async () => {
    fetchMock.mockResolvedValue(ok({ ErrorCode: 55 }));
    await expect(secugenProvider.match("A", "B")).rejects.toMatchObject({ code: 55 });
  });
});

describe("getProvider", () => {
  it("always returns the SecuGen provider", () => {
    expect(getProvider("secugen")).toBe(secugenProvider);
    expect(getProvider()).toBe(secugenProvider);
  });
});
