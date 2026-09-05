/**
 * Record Lifecycle Story.
 *
 * An animated vertical timeline that tells the full story of one healthcare
 * record: created -> anchored to blockchain -> corrected/erased via a real
 * chameleon-hash collision. It makes the invisible cryptography visible —
 * the single clearest way to explain the project's core innovation.
 */

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  FilePlus,
  Link2,
  FileEdit,
  Trash2,
  Activity,
  ChevronDown,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, truncateHash, cn } from "@/lib/utils";
import type { LifecycleEvent, RecordLifecycle } from "@/types";

const NODE: Record<
  LifecycleEvent["type"],
  { icon: LucideIcon; tint: string; ring: string; label: string }
> = {
  created: { icon: FilePlus, tint: "bg-primary-50 text-primary-600", ring: "ring-primary-100", label: "Created" },
  anchored: { icon: Link2, tint: "bg-primary-50 text-primary-600", ring: "ring-primary-100", label: "Anchored" },
  corrected: { icon: FileEdit, tint: "bg-warning/10 text-warning", ring: "ring-warning/20", label: "Corrected" },
  erased: { icon: Trash2, tint: "bg-danger/10 text-danger", ring: "ring-danger/20", label: "Erased" },
  audit: { icon: Activity, tint: "bg-neutral-100 text-neutral-500", ring: "ring-neutral-200", label: "Audit" },
};

function CollisionProof({ event }: { event: LifecycleEvent }) {
  const [open, setOpen] = useState(false);
  const c = event.chameleon_collision;
  if (!c) return null;

  return (
    <div className="mt-3 rounded-lg border border-neutral-200 bg-neutral-50/70 p-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="flex items-center gap-2 text-xs font-semibold text-neutral-700">
          <ShieldCheck className="h-4 w-4 text-primary-600" />
          Chameleon collision proof
          {c.verified && (
            <Badge variant="success" className="ml-1">verified</Badge>
          )}
        </span>
        <ChevronDown className={cn("h-4 w-4 text-neutral-400 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="mt-3 space-y-1.5 font-mono text-[11px] leading-relaxed text-neutral-600">
          <p className="font-sans text-xs text-neutral-500">
            The content changed but the chameleon hash stayed identical — so the
            blockchain anchor is still valid. That is the trapdoor collision:
          </p>
          <div className="rounded bg-white p-2 ring-1 ring-neutral-200">
            <div>CH = {truncateHash(c.chameleon_hash, 10)}</div>
            <div>r (original) = {truncateHash(c.original_r, 8)}</div>
            <div>r' (collision) = {truncateHash(c.collision_r, 8)}</div>
            <div>y (public key) = {truncateHash(c.public_key_y, 8)}</div>
            <div>modulus = {c.modulus_bits}-bit group</div>
          </div>
          <p className="font-sans text-[11px] text-neutral-400">
            CH(m, r) = g<sup>m</sup>·y<sup>r</sup> mod p&nbsp;&nbsp;→&nbsp;&nbsp;CH(m′, r′) with trapdoor x
          </p>
        </div>
      )}
    </div>
  );
}

export function RecordLifecycleStory({ lifecycle }: { lifecycle: RecordLifecycle }) {
  const events = useMemo(() => lifecycle.events ?? [], [lifecycle.events]);

  if (events.length === 0) {
    return <p className="py-8 text-center text-sm text-neutral-400">No lifecycle events yet.</p>;
  }

  return (
    <div className="relative">
      {/* Vertical spine */}
      <div className="absolute bottom-2 left-[19px] top-2 w-px bg-neutral-200" />

      <ul className="space-y-5">
        {events.map((ev, i) => {
          const meta = NODE[ev.type] ?? NODE.audit;
          const Icon = meta.icon;
          return (
            <motion.li
              key={`${ev.type}-${ev.timestamp}-${i}`}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: i * 0.06 }}
              className="relative flex gap-4"
            >
              <div
                className={cn(
                  "z-10 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full ring-4 ring-white",
                  meta.tint
                )}
              >
                <Icon className="h-5 w-5" />
              </div>

              <div className="flex-1 pb-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-neutral-900">{ev.title}</h4>
                  {ev.legal_basis && (
                    <Badge variant="secondary">{ev.legal_basis.replace("DPDP Act ", "")}</Badge>
                  )}
                </div>
                <p className="text-xs text-neutral-400">{formatDateTime(ev.timestamp)}</p>

                {ev.description && (
                  <p className="mt-1 text-sm text-neutral-600">{ev.description}</p>
                )}

                {ev.affected_fields && ev.affected_fields.length > 0 && (
                  <p className="mt-1 text-xs text-neutral-500">
                    Fields: {ev.affected_fields.join(", ")}
                  </p>
                )}

                {ev.type === "anchored" && ev.data_hash && (
                  <p className="mt-1 font-mono text-[11px] text-neutral-500">
                    hash {truncateHash(ev.data_hash, 10)}
                    {ev.block_number != null && ` · block #${ev.block_number}`}
                  </p>
                )}

                {ev.type === "anchored" && ev.explorer_url && (
                  <a
                    href={ev.explorer_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700"
                  >
                    View on block explorer ↗
                  </a>
                )}

                {(ev.type === "corrected" || ev.type === "erased") && (
                  <CollisionProof event={ev} />
                )}
              </div>
            </motion.li>
          );
        })}
      </ul>
    </div>
  );
}
