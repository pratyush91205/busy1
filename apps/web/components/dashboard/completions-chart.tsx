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
 * to decide what a missing week means - it draws what it is given. The bars
 * take the completed colour, so the chart agrees with every Completed badge on
 * the screen rather than introducing a sixth colour.
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
      <div className="h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 4, right: 4, bottom: 0, left: -26 }}
          >
            <CartesianGrid
              strokeDasharray="2 4"
              vertical={false}
              stroke="var(--border)"
            />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              fontSize={11}
              stroke="var(--muted-foreground)"
            />
            <YAxis
              // Whole services only: half a completion is not a thing.
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              width={34}
              stroke="var(--muted-foreground)"
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }}
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
                fontSize: 12,
              }}
              labelFormatter={(label) => `Week of ${label}`}
              formatter={(value) => [`${Number(value)} completed`, "Services"]}
            />
            <Bar dataKey="count" radius={[2, 2, 0, 0]} fill="var(--completed)" />
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
          No services completed in the last eight weeks. Quiet weeks are shown
          as zero rather than left out.
        </p>
      ) : null}
    </div>
  );
}

function shortDate(iso: string): string {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}
