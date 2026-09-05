/**
 * Brand Logo.
 *
 * Renders the DPDP Health shield logo. Imported as a module asset so
 * Vite fingerprints and bundles it. Use `size` to control the mark.
 */

import logoUrl from "@/assets/logo-256.png";
import { cn } from "@/lib/utils";

interface LogoProps {
  /** Pixel size of the square mark. */
  size?: number;
  /** Show the "DPDP Health" wordmark next to the icon. */
  withWordmark?: boolean;
  /** Optional subtitle under the wordmark. */
  subtitle?: string;
  className?: string;
}

export function Logo({ size = 36, withWordmark = false, subtitle, className }: LogoProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <img
        src={logoUrl}
        alt="DPDP Health logo"
        width={size}
        height={size}
        className="flex-shrink-0 rounded-xl object-contain"
        style={{ width: size, height: size }}
      />
      {withWordmark && (
        <div className="leading-tight">
          <div className="text-sm font-semibold text-neutral-800">DPDP Health</div>
          {subtitle && <div className="text-xs text-neutral-400">{subtitle}</div>}
        </div>
      )}
    </div>
  );
}

export { logoUrl };
