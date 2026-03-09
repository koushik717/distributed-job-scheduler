import { useState, useEffect, useCallback } from 'react'
import StatsCards from './components/StatsCards'
import Charts from './components/Charts'
import QueueDepth from './components/QueueDepth'
import JobsTable from './components/JobsTable'

const API_BASE = '/api'

export default function App() {
    const [stats, setStats] = useState(null)
    const [jobs, setJobs] = useState([])
    const [page, setPage] = useState(1)
    const [totalPages, setTotalPages] = useState(1)
    const [filter, setFilter] = useState('')
    const [loading, setLoading] = useState(true)
    const [autoRefresh, setAutoRefresh] = useState(true)
    const [lastUpdated, setLastUpdated] = useState(null)

    const fetchStats = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/jobs/stats/`)
            if (res.ok) {
                const data = await res.json()
                setStats(data)
            }
        } catch (err) {
            console.error('Failed to fetch stats:', err)
        }
    }, [])

    const fetchJobs = useCallback(async () => {
        try {
            let url = `${API_BASE}/jobs/?page=${page}&ordering=-created_at`
            if (filter) url += `&status=${filter}`
            const res = await fetch(url)
            if (res.ok) {
                const data = await res.json()
                setJobs(data.results || [])
                const count = data.count || 0
                setTotalPages(Math.ceil(count / 20) || 1)
            }
        } catch (err) {
            console.error('Failed to fetch jobs:', err)
        }
    }, [page, filter])

    const fetchAll = useCallback(async () => {
        setLoading(true)
        await Promise.all([fetchStats(), fetchJobs()])
        setLastUpdated(new Date())
        setLoading(false)
    }, [fetchStats, fetchJobs])

    useEffect(() => {
        fetchAll()
    }, [fetchAll])

    useEffect(() => {
        if (!autoRefresh) return
        const interval = setInterval(fetchAll, 3000)
        return () => clearInterval(interval)
    }, [autoRefresh, fetchAll])

    const handleAction = async (jobId, action) => {
        try {
            const res = await fetch(`${API_BASE}/jobs/${jobId}/${action}/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            if (res.ok) {
                fetchAll()
            }
        } catch (err) {
            console.error(`Failed to ${action} job:`, err)
        }
    }

    return (
        <div className="app">
            <header className="header">
                <div className="header-left">
                    <div className="header-icon">⚡</div>
                    <div>
                        <h1>Job Scheduler</h1>
                        <p>Distributed Async Processing Dashboard</p>
                    </div>
                </div>
                <div className="header-right">
                    {autoRefresh && <div className="live-dot" />}
                    <label className="auto-refresh">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                        />
                        Auto-refresh
                    </label>
                    <button
                        className={`refresh-btn ${loading ? 'loading' : ''}`}
                        onClick={fetchAll}
                        disabled={loading}
                    >
                        ↻ Refresh
                    </button>
                    {lastUpdated && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {lastUpdated.toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </header>

            <StatsCards stats={stats} loading={loading} />
            <Charts stats={stats} />
            <QueueDepth stats={stats} />
            <JobsTable
                jobs={jobs}
                filter={filter}
                setFilter={setFilter}
                page={page}
                setPage={setPage}
                totalPages={totalPages}
                onAction={handleAction}
                loading={loading}
            />
        </div>
    )
}
