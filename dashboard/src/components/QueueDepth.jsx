export default function QueueDepth({ stats }) {
    if (!stats?.queue_depth) return null

    const queues = [
        {
            name: 'High Priority',
            key: 'high_priority',
            value: stats.queue_depth.high_priority || 0,
            colorClass: 'high',
            icon: '🔴',
        },
        {
            name: 'Default',
            key: 'default',
            value: stats.queue_depth.default || 0,
            colorClass: 'default',
            icon: '🔵',
        },
        {
            name: 'Low Priority',
            key: 'low_priority',
            value: stats.queue_depth.low_priority || 0,
            colorClass: 'low',
            icon: '🟢',
        },
    ]

    const maxValue = Math.max(...queues.map(q => q.value), 1)

    return (
        <div className="queue-section">
            <h3>⚡ Queue Depth</h3>
            <div className="queue-bars">
                {queues.map(queue => (
                    <div key={queue.key} className="queue-bar-card">
                        <div className="queue-bar-label">
                            {queue.icon} {queue.name}
                        </div>
                        <div className="queue-bar-value" style={{ color: getColor(queue.colorClass) }}>
                            {queue.value.toLocaleString()}
                        </div>
                        <div className="queue-bar-track">
                            <div
                                className={`queue-bar-fill ${queue.colorClass}`}
                                style={{ width: `${(queue.value / maxValue) * 100}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

function getColor(cls) {
    switch (cls) {
        case 'high': return '#f87171'
        case 'default': return '#818cf8'
        case 'low': return '#34d399'
        default: return '#94a3b8'
    }
}
