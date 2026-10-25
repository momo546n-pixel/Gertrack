export default function Skeleton({ width = '100%', height = '16px', radius = 'var(--radius-sm)', style }) {
  return (
    <div
      className="ds-skeleton"
      style={{ width, height, borderRadius: radius, ...style }}
    />
  );
}
