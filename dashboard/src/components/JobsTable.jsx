const TYPE_ICONS = {
    send_email: '📧',
    generate_report: '📊',
    process_data: '⚙️',
    cleanup: '🧹',
    webhook: '🔗',
    image_resize: '🖼️',
}

const STATUS_FILTERS = ['', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'DEAD', 'CANCELLED']

export default function JobsTable({
    jobs, filter, setFilter, page, setPage, totalPages, onAction, loading
}) {
    return (
        <div className="table-section">
            <div className="table-header">
                <h3>📋 Jobs</h3>
                <div className="table-filters">
                    {STATUS_FILTERS.map(s => (
                        <button
                            key={s}
                            className={`filter-btn ${filter === s ? 'active' : ''}`}
                            onClick={() => { setFilter(s); setPage(1) }}
                        >
                            {s || 'All'}
                        </button>
                    ))}
                </div>
            </div>

            {jobs.length === 0 ? (
                <div className="empty-state">
                    <div className="icon">📭</div>
                    <p>{loading ? 'Loading jobs...' : 'No jobs found'}</p>
                </div>
            ) : (
                <>
                    <div style={{ overflowX: 'auto' }}>
                        <table className="jobs-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Type</th>
                                    <th>Status</th>
                                    <th>Priority</th>
                                    <th>Retries</th>
                                    <th>Duration</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {jobs.map(job => (
                                    <tr key={job.id}>
                                        <td className="job-id">{job.id.slice(0, 8)}</td>
                                        <td>
                                            <span className="job-type">
                                                {TYPE_ICONS[job.type] || '📦'} {job.type}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`status-badge ${job.status.toLowerCase()}`}>
                                                {job.status}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`priority-badge ${getPriorityClass(job.priority)}`}>
                                                {job.priority}
                                            </span>
                                        </td>
                                        <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                                            {job.retry_count}/{job.max_retries}
                                        </td>
                                        <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                                            {job.duration_seconds != null
                                                ? `${job.duration_seconds.toFixed(2)}s`
                                                : '—'}
                                        </td>
                                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                            {formatTime(job.created_at)}
                                        </td>
                                        <td>
                                            {(job.status === 'PENDING' || job.status === 'SCHEDULED') && (
                                                <button
                                                    className="action-btn danger"
                                                    onClick={() => onAction(job.id, 'cancel')}
                                                >
                                                    Cancel
                                                </button>
                                            )}
                                            {(job.status === 'DEAD' || job.status === 'FAILED') && (
                                                <button
                                                    className="action-btn"
                                                    onClick={() => onAction(job.id, 'retry')}
                                                >
                                                    Retry
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="pagination">
                        <div className="pagination-info">
                            Page {page} of {totalPages}
                        </div>
                        <div className="pagination-btns">
                            <button
                                className="page-btn"
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page <= 1}
                            >
                                ← Previous
                            </button>
                            <button
                                className="page-btn"
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page >= totalPages}
                            >
                                Next →
                            </button>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}

function getPriorityClass(p) {
    if (p <= 3) return 'high'
    if (p <= 7) return 'medium'
    return 'low'
}

function formatTime(isoString) {
    if (!isoString) return '—'
    const d = new Date(isoString)
    return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    })
}
