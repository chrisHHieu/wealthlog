export function SkeletonKPI() {
  return (
    <div className="kpi-card">
      <div className="skeleton" style={{ height: 14, width: '60%', marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 32, width: '80%', marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 12, width: '40%' }} />
    </div>
  )
}
