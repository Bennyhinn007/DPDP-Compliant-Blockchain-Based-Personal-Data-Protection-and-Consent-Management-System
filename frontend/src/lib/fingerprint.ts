/**
 * Fingerprint provider abstraction (browser side).
 *
 * HONEST LIMITATION (prototype): capture AND matching are done here in the
 * browser by the vendor's local service (SecuGen WebAPI / SgiBioSrv at
 * https://localhost:8443). The backend only receives the resulting match score and
 * TRUSTS it. A malicious client can report any score, so this is a prototype
 * second factor, not tamper-proof. The enrolled template is also released to any
 * client holding a valid pending-login token (which needs the correct password).
 *
 * The SecuGen service runs on the admin's own PC, so this only works on the
 * machine where the reader is plugged in.
 */

export const SECUGEN = {
  BASE_URL: "https://localhost:8443",
  CAPTURE: "/SGIFPCapture",
  MATCH: "/SGIMatchScore",
  TIMEOUT_MS: 10000,
  QUALITY: 50,
  TEMPLATE_FORMAT: "ISO",
  WSQ_RATE: "0.75",
} as const;

/** License string emailed by SecuGen for the WebAPI trial (optional). */
const LICSTR: string = (import.meta.env.VITE_SECUGEN_LICSTR as string | undefined) ?? "";

export const NETWORK_ERROR_MESSAGE =
  "SecuGen service not reachable. Install SecuGen WebAPI and open https://localhost:8443 once to accept the certificate.";

const LICENSE_MESSAGE = "SecuGen license problem. Check VITE_SECUGEN_LICSTR / WebAPI license.";

const ERROR_MESSAGES: Record<number, string> = {
  54: "Fingerprint capture timed out. Place your finger on the reader and try again.",
  55: "SecuGen reader not found. Check that the reader is plugged in.",
  10001: LICENSE_MESSAGE,
  10002: LICENSE_MESSAGE,
  10003: LICENSE_MESSAGE,
  10004: "SecuGen service access/license error. Check the SecuGen WebAPI license.",
};

export class FingerprintError extends Error {
  code?: number;
  constructor(message: string, code?: number) {
    super(message);
    this.name = "FingerprintError";
    this.code = code;
  }
}

export interface CaptureResult {
  template: string;
  quality: number;
  previewBmpBase64?: string;
}

export interface FingerprintProvider {
  id: "secugen" | "mantra";
  capture(): Promise<CaptureResult>;
  match(template1: string, template2: string): Promise<number>;
}

function messageForCode(code: number): string {
  return ERROR_MESSAGES[code] ?? `SecuGen error (code ${code}).`;
}

async function secugenPost(path: string, params: Record<string, string>): Promise<Record<string, unknown>> {
  let response: Response;
  try {
    response = await fetch(`${SECUGEN.BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params),
    });
  } catch {
    throw new FingerprintError(NETWORK_ERROR_MESSAGE);
  }
  if (!response.ok) throw new FingerprintError(NETWORK_ERROR_MESSAGE);
  let json: Record<string, unknown>;
  try {
    json = (await response.json()) as Record<string, unknown>;
  } catch {
    throw new FingerprintError(NETWORK_ERROR_MESSAGE);
  }
  const code = Number(json.ErrorCode ?? 0);
  if (code !== 0) throw new FingerprintError(messageForCode(code), code);
  return json;
}

export const secugenProvider: FingerprintProvider = {
  id: "secugen",

  async capture(): Promise<CaptureResult> {
    const json = await secugenPost(SECUGEN.CAPTURE, {
      Timeout: String(SECUGEN.TIMEOUT_MS),
      Quality: String(SECUGEN.QUALITY),
      licstr: LICSTR,
      templateFormat: SECUGEN.TEMPLATE_FORMAT,
      imageWSQRate: SECUGEN.WSQ_RATE,
    });
    const template = String(json.TemplateBase64 ?? "");
    if (!template) throw new FingerprintError("No fingerprint template was captured. Try again.");
    return {
      template,
      quality: Number(json.ImageQuality ?? 0),
      previewBmpBase64: json.BMPBase64 ? String(json.BMPBase64) : undefined,
    };
  },

  async match(template1: string, template2: string): Promise<number> {
    const json = await secugenPost(SECUGEN.MATCH, {
      Template1: template1,
      Template2: template2,
      licstr: LICSTR,
      templateFormat: SECUGEN.TEMPLATE_FORMAT,
    });
    return Number(json.MatchingScore ?? 0);
  },
};

/**
 * TODO: Mantra MFS100 adapter is NOT implemented. This stub throws on purpose and
 * returns no fake data.
 */
export const mantraProvider: FingerprintProvider = {
  id: "mantra",
  async capture(): Promise<CaptureResult> {
    throw new FingerprintError("Mantra adapter not implemented");
  },
  async match(): Promise<number> {
    throw new FingerprintError("Mantra adapter not implemented");
  },
};

export function getProvider(id: string): FingerprintProvider {
  return id === "mantra" ? mantraProvider : secugenProvider;
}
