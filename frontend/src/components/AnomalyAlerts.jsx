import { useState, useEffect } from 'react'
import { AlertTriangle, TrendingDown, Users, ShieldAlert, CheckCircle2, ChevronRight } from 'lucide-react'
import { getAnomalies } from '../services/api'

export default function AnomalyAlerts() {
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let isMounted = true
    async function load() {
      try {
        const data = await getAnomalies()
        if (isMounted && data && data.anomalies) {
          setAnomalies(data.anomalies)
        }
      } catch (err) {
        console.warn('Failed to fetch anomalies:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    load()
    return () => { isMounted = false }
  }, [])

  if (loading || anomalies.length === 0) return null

  const displayList = expanded ? anomalies : anomalies.slice(0, 2)

  return (
    <div className="bg-amber-50/80 border border-amber-200/90 rounded-2xl p-5 text-slate-800 shadow-sm transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-500/20 text-amber-700 flex items-center justify-center font-bold">
            <ShieldAlert size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
              Financial Anomaly Detection
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-200/80 text-amber-800">
                {anomalies.length} Advisory Alert{anomalies.length > 1 ? 's' : ''}
              </span>
            </h3>
            <p className="text-xs text-slate-600">
              Statistical variance alerts across payment retries, customer aging, and transaction spikes.
            </p>
          </div>
        </div>
        {anomalies.length > 2 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-medium text-amber-900 hover:text-amber-700 hover:underline flex items-center gap-1 transition-colors"
          >
            {expanded ? 'Show Less' : `View All (${anomalies.length})`}
            <ChevronRight size={14} className={`transform transition-transform ${expanded ? '-rotate-90' : 'rotate-90'}`} />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
        {displayList.map((a) => (
          <div
            key={a.anomaly_id}
            className="bg-white/90 border border-amber-200/60 rounded-xl p-3.5 shadow-2xs hover:shadow-sm transition-shadow"
          >
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <span className="text-xs font-bold text-slate-900 truncate">{a.title}</span>
              <span
                className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                  a.severity === 'high'
                    ? 'bg-rose-100 text-rose-700'
                    : 'bg-amber-100 text-amber-700'
                }`}
              >
                {a.severity}
              </span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed mb-2">{a.description}</p>
            <div className="text-[11px] text-amber-900 bg-amber-50/80 rounded-lg p-2 border border-amber-100 italic">
              💡 {a.explanation}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

