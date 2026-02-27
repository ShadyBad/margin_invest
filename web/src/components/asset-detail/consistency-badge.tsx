"use client";

interface ConsistencyWarning {
  field_name: string;
  z_score: number;
  current_value: number;
  historical_mean: number;
}

interface ConsistencyBadgeProps {
  warnings: ConsistencyWarning[];
}

const FIELD_LABELS: Record<string, string> = {
  revenue: "Revenue",
  total_assets: "Total Assets",
  shares_outstanding: "Shares Outstanding",
  operating_income: "Operating Income",
  free_cash_flow: "Free Cash Flow",
};

export function ConsistencyBadge({ warnings }: ConsistencyBadgeProps) {
  if (warnings.length === 0) return null;

  return (
    <div
      data-testid="consistency-badge"
      className="flex items-center gap-2 rounded-md border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-3 py-1.5 text-xs"
    >
      <span className="font-mono font-semibold text-[var(--color-warning)]">
        DATA ANOMALY
      </span>
      <span className="text-[var(--color-muted)]">
        {warnings
          .map((w) => FIELD_LABELS[w.field_name] || w.field_name)
          .join(", ")}{" "}
        deviated &gt;3&#963; from history
      </span>
    </div>
  );
}
