import { Doughnut, Bar } from 'react-chartjs-2'
import {
    Chart as ChartJS,
    ArcElement,
    Tooltip,
    Legend,
    CategoryScale,
    LinearScale,
    BarElement,
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

const chartColors = {
    completed: '#10b981',
    running: '#3b82f6',
    pending: '#f59e0b',
    failed: '#ef4444',
    dead: '#dc2626',
    scheduled: '#8b5cf6',
    cancelled: '#6b7280',
}

export default function Charts({ stats }) {
    if (!stats) return null

    const statusData = {
        labels: ['Completed', 'Running', 'Pending', 'Failed', 'Dead', 'Scheduled', 'Cancelled'],
        datasets: [{
            data: [
                stats.completed || 0,
                stats.running || 0,
                stats.pending || 0,
                stats.failed || 0,
                stats.dead || 0,
                stats.scheduled || 0,
                stats.cancelled || 0,
            ],
            backgroundColor: [
                chartColors.completed,
                chartColors.running,
                chartColors.pending,
                chartColors.failed,
                chartColors.dead,
                chartColors.scheduled,
                chartColors.cancelled,
            ],
            borderWidth: 0,
            hoverOffset: 8,
        }],
    }

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    color: '#94a3b8',
                    font: { family: "'Inter', sans-serif", size: 12 },
                    padding: 16,
                    usePointStyle: true,
                    pointStyleWidth: 10,
                },
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f1f5f9',
                bodyColor: '#94a3b8',
                borderColor: 'rgba(99, 102, 241, 0.3)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
                titleFont: { family: "'Inter', sans-serif", weight: 600 },
                bodyFont: { family: "'JetBrains Mono', monospace" },
            },
        },
    }

    // Queue depth bar chart
    const queueData = stats.queue_depth || {}
    const barData = {
        labels: ['High Priority', 'Default', 'Low Priority'],
        datasets: [{
            label: 'Jobs in Queue',
            data: [
                queueData.high_priority || 0,
                queueData.default || 0,
                queueData.low_priority || 0,
            ],
            backgroundColor: [
                'rgba(239, 68, 68, 0.6)',
                'rgba(99, 102, 241, 0.6)',
                'rgba(16, 185, 129, 0.6)',
            ],
            borderColor: [
                'rgba(239, 68, 68, 0.8)',
                'rgba(99, 102, 241, 0.8)',
                'rgba(16, 185, 129, 0.8)',
            ],
            borderWidth: 1,
            borderRadius: 8,
        }],
    }

    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#f1f5f9',
                bodyColor: '#94a3b8',
                borderColor: 'rgba(99, 102, 241, 0.3)',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    color: '#64748b',
                    font: { family: "'Inter', sans-serif", size: 12 },
                },
            },
            y: {
                grid: { color: 'rgba(255, 255, 255, 0.04)' },
                ticks: {
                    color: '#64748b',
                    font: { family: "'JetBrains Mono', monospace", size: 11 },
                },
                beginAtZero: true,
            },
        },
    }

    return (
        <div className="charts-grid">
            <div className="chart-card">
                <h3>📊 Job Status Distribution</h3>
                <div className="chart-container">
                    <Doughnut data={statusData} options={doughnutOptions} />
                </div>
            </div>
            <div className="chart-card">
                <h3>📦 Queue Depth</h3>
                <div className="chart-container">
                    <Bar data={barData} options={barOptions} />
                </div>
            </div>
        </div>
    )
}
