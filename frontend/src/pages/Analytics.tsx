import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, TrendingUp } from 'lucide-react'
import { aiSystemsApi, analyticsApi } from '../services/api'

/**
 * Analytics page — compliance score timeline and aggregate stats.
 * Backed by GET /api/v1/analytics/summary and
 * GET /api/v1/analytics/compliance-timeline?system_id=X.
 */

interface AISystem {
  id: number
  name: string
}

export default function Analytics() {
  const [selectedSystem, setSelectedSystem] = useState<number | null>(null)

  const { data: summary } = useQuery({
    queryKey: ['analytics', 'summary'],
    queryFn: analyticsApi.summary,
  })

  const { data: systems = [] } = useQuery<AISystem[]>({
    queryKey: ['ai-systems'],
    queryFn: aiSystemsApi.list,
  })

  useEffect(() => {
    if (selectedSystem === null && systems.length > 0) {
      setSelectedSystem(systems[0].id)
    }
  }, [systems, selectedSystem])

  const { data: timeline } = useQuery({
    queryKey: ['analytics', 'timeline', selectedSystem],
    queryFn: () => analyticsApi.timeline(selectedSystem as number),
    enabled: selectedSystem !== null,
  })

  const snapshots = timeline?.snapshots ?? []
  const scoredSnapshots = snapshots.filter(
    (snapshot) => snapshot.compliance_score !== null
  )

  const cards = [
    { label: 'Total Systems', value: summary ? summary.total_systems : '—' },
    {
      label: 'Avg Score',
      value:
        summary?.average_compliance_score !== null &&
        summary?.average_compliance_score !== undefined
          ? `${summary.average_compliance_score}`
          : '—',
    },
    {
      label: 'Compliant',
      value: summary ? summary.by_compliance_status.compliant ?? 0 : '—',
    },
    {
      label: 'High Risk',
      value: summary ? summary.by_risk_level.high ?? 0 : '—',
    },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-600">Compliance score trends over time</p>
      </div>

      {/* Summary stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm text-gray-500">{card.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Chart area */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between gap-2 mb-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">Compliance Score Timeline</h2>
          </div>
          <select
            value={selectedSystem ?? ''}
            onChange={(e) => setSelectedSystem(Number(e.target.value))}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg"
            aria-label="Select AI system"
          >
            {systems.length === 0 && <option value="">No systems yet</option>}
            {systems.map((system) => (
              <option key={system.id} value={system.id}>
                {system.name}
              </option>
            ))}
          </select>
        </div>

        {scoredSnapshots.length === 0 ? (
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg border border-dashed border-gray-300">
            <div className="text-center text-gray-400">
              <BarChart2 className="w-12 h-12 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No compliance snapshots yet</p>
              <p className="text-xs mt-1">
                Scores appear once the daily snapshot job has recorded history.
              </p>
            </div>
          </div>
        ) : (
          <div className="h-64">
            <svg
              viewBox="0 0 300 100"
              preserveAspectRatio="none"
              className="w-full h-full"
              role="img"
              aria-label="Compliance score timeline"
            >
              <polyline
                fill="none"
                stroke="#2563eb"
                strokeWidth="2"
                points={scoredSnapshots
                  .map((snapshot, index) => {
                    const x =
                      scoredSnapshots.length === 1
                        ? 0
                        : (index / (scoredSnapshots.length - 1)) * 300
                    const y = 100 - (Number(snapshot.compliance_score) / 100) * 100
                    return `${x},${y}`
                  })
                  .join(' ')}
              />
            </svg>
          </div>
        )}
      </div>
    </div>
  )
}
