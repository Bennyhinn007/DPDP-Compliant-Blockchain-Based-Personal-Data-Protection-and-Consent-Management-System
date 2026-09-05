/**
 * Compliance Score Gauge.
 *
 * Semi-circular radial gauge showing 0-100 compliance score.
 */

import { motion } from "framer-motion";

interface ComplianceGaugeProps {
  score: number;
  grade: string;
}

export function ComplianceGauge({ score, grade }: ComplianceGaugeProps) {
  const radius = 80;
  const circumference = Math.PI * radius; // half circle
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 90 ? "#16A34A" : score >= 70 ? "#6366F1" : score >= 50 ? "#D97706" : "#DC2626";

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="120" viewBox="0 0 200 120">
        {/* Background arc */}
        <path
          d="M 20 110 A 80 80 0 0 1 180 110"
          fill="none"
          stroke="#E5E7EB"
          strokeWidth="14"
          strokeLinecap="round"
        />
        {/* Foreground arc */}
        <motion.path
          d="M 20 110 A 80 80 0 0 1 180 110"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="-mt-8 text-center">
        <div className="text-4xl font-bold text-neutral-800">{score}</div>
        <div className="text-sm text-neutral-400">out of 100</div>
        <div
          className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white"
          style={{ backgroundColor: color }}
        >
          {grade}
        </div>
      </div>
    </div>
  );
}
