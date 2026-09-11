"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Services completed per ISO week, eight buckets.
 *
 * The server sends exactly eight, zeros included, so this component never has
 * to decide what a missing week means - it draws what it is given.
 */
export function CompletionsChart({
  data,
}: {
  data: { week_start: string; count: number }[];
}) {
  const chartData = data.map((row) => ({
    ...row,
    label: shortDate(row.week_start),
  }));

  const busiest = Math.max(...data.map((row) => row.count), 0);

  return (
    <div className="space-y-2">
      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 4, right: 4, bottom: 0, left: -24 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              fontSize={11}
            />
            <YAxis
              // Whole services only: half a completion is not a thing.
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              width={32}
            />
            <Tooltip
              cursor={{ fillOpacity: 0.08 }}
              labelFormatter={(label) => `Week of ${label}`}
              formatter={(value) => [`${Number(value)} completed`, "Services"]}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]} fill="currentColor" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* The chart is not the only way to read this: a screen reader gets the
          same numbers, and so does anyone for whom the bars are too short to
          compare. */}
      <p className="sr-only">
        {chartData
          .map((row) => `Week of ${row.label}: ${row.count} completed`)
          .join(". ")}
      </p>

      {busiest === 0 ? (
        <p className="text-muted-foreground text-xs">
          No services completed in the last eight weeks.
        </p>
      ) : null}
    </div>
  );
}

function shortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}
