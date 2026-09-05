/**
 * Physical Access Log — Live RFID Terminal Feed.
 *
 * Shows real-time physical RFID verification events from the ESP32 hardware
 * terminal. Polls every 3 seconds so a card tap appears live on screen.
 */

import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Nfc,
  ShieldCheck,
  ShieldX,
  CheckCircle2,
  XCircle,
  CreditCard,
} from "lucide-react";
import { adminService, type PhysicalAccessEvent } from "@/services/adminService";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatCard } from "@/components/shared/StatCard";
import { PageHero } from "@/components/shared/PageHero";
import { PageLoader } from "@/components/shared/PageLoader";
import { formatDateTime } from "@/lib/utils";

export function PhysicalAccessLog() {
  const { data, isLoading } = useQuery({
    queryKey: ["physical-access-log"],
    queryFn: () => adminService.getPhysicalAccessLog(30),
    refetchInterval: 3000, // live polling — a tap appears within 3 seconds
  });

  if (isLoading && !data) return <PageLoader message="Loading Physical Access Log..." />;

  const events = data?.events ?? [];
  const stats = data?.stats ?? { total: 0, granted: 0, denied: 0 };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHero
        title="Physical Access Log"
        subtitle="Live RFID verification events from the hardware terminal"
        icon={Nfc}
        pill={{ label: "Live · Auto-refresh", tone: "success" }}
      />

      {/* Stats */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard label="Total Taps" value={stats.total} icon={Nfc} variant="primary" subtitle="Physical verifications" />
        <StatCard label="Access Granted" value={stats.granted} icon={ShieldCheck} variant="success" subtitle="Valid cards" />
        <StatCard label="Access Denied" value={stats.denied} icon={ShieldX} variant="warning" subtitle="Unknown cards" />
      </div>

      {/* Live Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4 text-primary-600" />
            Live Terminal Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="py-16 text-center">
              <Nfc className="mx-auto h-12 w-12 text-neutral-300" />
              <p className="mt-4 text-sm text-neutral-400">
                No RFID taps yet. Tap a card on the hardware terminal — it will appear here live.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <AnimatePresence initial={false}>
                {events.map((event) => (
                  <AccessRow key={event._id} event={event} />
                ))}
              </AnimatePresence>
            </div>
          )}
        </CardContent>
      </Card>

      {/* How it works note */}
      <Card>
        <CardContent className="flex items-start gap-3 py-4">
          <Nfc className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary-600" />
          <div className="text-sm text-neutral-600">
            <p className="font-medium text-neutral-800">How physical verification works</p>
            <p className="mt-1 text-xs">
              A user taps their RFID card on the ESP32 terminal. The RC522 reader reads the card,
              the ESP32 sends it over WiFi to the backend, which verifies the identity, records this
              event in the blockchain-anchored audit trail, and returns the access decision — all in
              under a second. Every tap you see below is a real physical verification event.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AccessRow({ event }: { event: PhysicalAccessEvent }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex items-center justify-between rounded-lg border px-4 py-3 ${
        event.granted ? "border-success/30 bg-success/5" : "border-danger/30 bg-danger/5"
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-md ${
            event.granted ? "bg-success/10" : "bg-danger/10"
          }`}
        >
          {event.granted ? (
            <CheckCircle2 className="h-5 w-5 text-success" />
          ) : (
            <XCircle className="h-5 w-5 text-danger" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-neutral-800">{event.reason}</p>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-neutral-400">
            <span className="font-mono">Card: {event.card_id}</span>
            <span>·</span>
            <span className="capitalize">{event.actor_role}</span>
            <span>·</span>
            <span>{formatDateTime(event.created_at)}</span>
          </div>
        </div>
      </div>
      <Badge variant={event.granted ? "success" : "danger"}>
        {event.granted ? "Granted" : "Denied"}
      </Badge>
    </motion.div>
  );
}
