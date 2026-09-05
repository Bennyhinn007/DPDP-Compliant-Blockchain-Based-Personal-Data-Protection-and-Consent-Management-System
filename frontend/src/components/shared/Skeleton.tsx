/**
 * Skeleton Loaders.
 *
 * Shimmer placeholders used while data loads, instead of blank screens
 * or bare spinners. Mirrors the shape of the real content.
 */

import { cn } from "@/lib/utils";

/** Base shimmer block. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-neutral-200/70",
        "before:absolute before:inset-0 before:-translate-x-full",
        "before:animate-[shimmer_1.6s_infinite]",
        "before:bg-gradient-to-r before:from-transparent before:via-white/60 before:to-transparent",
        className
      )}
    />
  );
}

/** A skeleton shaped like a StatCard. */
export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-neutral-200/70 bg-white/95 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-2 w-20" />
        </div>
        <Skeleton className="h-12 w-12 rounded-xl" />
      </div>
    </div>
  );
}

/** A skeleton shaped like a content card. */
export function CardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-neutral-200/70 bg-white/95 p-6 shadow-sm">
      <Skeleton className="h-5 w-40" />
      <div className="mt-5 space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-2 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/** A full dashboard-shaped skeleton: stat row + two cards. */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full rounded-2xl" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}
