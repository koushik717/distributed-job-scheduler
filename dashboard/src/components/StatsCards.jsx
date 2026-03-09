export default function StatsCards({ stats, loading }) {
    if (!stats && loading) {
        return (
            <div className="stats-grid">
                {Array.from({ length: 7 }).map((_, i) => (
                    <div key={i} className="stat-card loading-shimmer" style={{ height: 100 }} />
                ))}
            </div>
        )
    }

    if (!stats) return null

    const cards = [
        {
            label: 'Total Jobs',
            value: stats.total_jobs?.toLocaleString() || '0',
            className: '',
            subtitle: 'All time',
        },
        {
            label: 'Completed',
            value: stats.completed?.toLocaleString() || '0',
            className: 'success',
            subtitle: `${stats.success_rate || 0}% success rate`,
        },
        {
            label: 'Running',
            value: stats.running?.toLocaleString() || '0',
            className: 'info',
            subtitle: 'Currently processing',
        },
        {
            label: 'Pending',
            value: stats.pending?.toLocaleString() || '0',
            className: 'warning',
            subtitle: 'In queue',
        },
        {
            label: 'Failed',
            value: stats.failed?.toLocaleString() || '0',
            className: 'danger',
            subtitle: 'Awaiting retry',
        },
        {
            label: 'Dead (DLQ)',
            value: stats.dead?.toLocaleString() || '0',
            className: 'danger',
            subtitle: 'Retries exhausted',
        },
        {
            label: 'Avg Duration',
            value: stats.avg_duration_seconds
                ? `${stats.avg_duration_seconds.toFixed(2)}s`
                : '—',
            className: 'purple',
            subtitle: 'Processing time',
        },
    ]

    return (
        <div className="stats-grid">
            {cards.map((card, i) => (
                <div className="stat-card" key={i}>
                    <div className="label">{card.label}</div>
                    <div className={`value ${card.className}`}>{card.value}</div>
                    <div className="subtitle">{card.subtitle}</div>
                </div>
            ))}
        </div>
    )
}
