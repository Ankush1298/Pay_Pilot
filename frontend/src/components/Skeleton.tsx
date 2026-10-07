/** Shimmer placeholder. The shimmer moves with transform only (see .skeleton in site.css). */
export function Skeleton({ h = 16, w = "100%", r = 8, className = "" }: { h?: number | string; w?: number | string; r?: number; className?: string }) {
  return <div className={`skeleton ${className}`} style={{ height: h, width: w, borderRadius: r }} aria-hidden="true" />;
}

export function DashboardSkeleton() {
  return (
    <div className="page" role="status" aria-label="Loading your dashboard">
      <Skeleton h={34} w="40%" /><div style={{ height: 10 }} /><Skeleton h={16} w="60%" />
      <div className="skel-grid">
        <Skeleton h={260} r={14} /><Skeleton h={520} r={14} /><Skeleton h={260} r={14} />
      </div>
    </div>
  );
}
