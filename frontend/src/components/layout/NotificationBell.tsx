/**
 * Notification Bell.
 *
 * Displays recent audit events as notifications.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { auditService } from "@/services/auditService";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  const { data: events = [] } = useQuery({
    // Same key and request as the patient dashboard timeline, so React Query
    // sends one GET /audit/timeline instead of two.
    queryKey: ["timeline"],
    queryFn: () => auditService.getTimeline(),
    enabled: user?.role === "patient",
    staleTime: 60_000,
  });

  const recentEvents = events.slice(0, 5);
  const unreadCount = Math.min(recentEvents.length, 3);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative flex h-10 w-10 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger text-[10px] font-bold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border border-neutral-200 bg-white shadow-lg">
            <div className="border-b border-neutral-200 px-4 py-3">
              <h3 className="text-sm font-semibold text-neutral-800">Recent Activity</h3>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {recentEvents.length === 0 ? (
                <div className="px-4 py-6 text-center text-xs text-neutral-400">No recent events</div>
              ) : (
                recentEvents.map((event) => (
                  <div
                    key={event._id}
                    className={cn("border-b border-neutral-100 px-4 py-3 hover:bg-neutral-50")}
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-sm font-medium text-neutral-800">
                        {event.action_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                      <span className="text-xs text-neutral-400">
                        {new Date(event.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-neutral-500">{event.reason}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
