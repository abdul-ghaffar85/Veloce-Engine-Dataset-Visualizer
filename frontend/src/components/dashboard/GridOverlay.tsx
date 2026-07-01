import React from 'react';

interface GridOverlayProps {
  cols: number;
  rowHeight: number;
  margin: [number, number];
  minRows?: number;
  contentRows?: number;
}

/**
 * Visual snap-grid guide shown behind widgets in Edit Mode.
 * `cols` is driven by ResponsiveGridLayout's own onBreakpointChange callback
 * (see DashboardCanvas) rather than an independent width measurement, so the
 * overlay is guaranteed to match the grid's real column count/breakpoint.
 */
export const GridOverlay: React.FC<GridOverlayProps> = ({
  cols,
  rowHeight,
  margin,
  minRows = 8,
  contentRows = 0,
}) => {
  const [marginX, marginY] = margin;
  const rows = Math.max(minRows, contentRows + 2);

  return (
    <div
      className="absolute inset-0 z-0 pointer-events-none animate-in fade-in duration-200"
      style={{ padding: marginX }}
    >
      <div
        className="grid w-full h-full"
        style={{
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridAutoRows: rowHeight,
          columnGap: marginX,
          rowGap: marginY,
        }}
      >
        {Array.from({ length: cols * rows }).map((_, i) => (
          <div
            key={i}
            className="rounded-sm border border-dashed border-brand-500/[0.12] bg-brand-500/[0.02]"
          />
        ))}
      </div>
    </div>
  );
};
