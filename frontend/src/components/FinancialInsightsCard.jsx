import { useState, useEffect } from 'react'
import { Sparkles, TrendingUp, TrendingDown, HelpCircle, ArrowRight } from 'lucide-react'
import { getFinancialIntelligence } from '../services/api'

export default function FinancialInsightsCard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    async function load() {
      try {
        const res = await getFinancialIntelligence()
        if (isMounted && res) {
          setData(res)
        }
      } catch (err) {
        console.warn('Financial intelligence error:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    load()
    return () => { isMounted = false }
  }, [])

  if (loading || !data) return null

  const mom = data.mom_comparison || {}
  const forecast = data.forecast || {}
  const isUp = mom.trend_direction === 'up'

  return (
    <div className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white rounded-2xl p-6 shadow-md border border-indigo-800/40 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold">
              <Sparkles size={18} />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">AI Financial Analyst</h3>
              <p className="text-xs text-indigo-200/70">Database Grounded Growth & Forecast</p>
            </div>
          </div>
          <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-800 text-indigo-200">
            Realtime Analytics
          </span>
        </div>

        {/* MoM Performance */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3.5 mb-4 backdrop-blur-xs">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-indigo-200">Month-over-Month Growth</span>
            <div className={`flex items-center gap-1 text-xs font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {mom.growth_rate_pct > 0 ? `+${mom.growth_rate_pct}%` : `${mom.growth_rate_pct}%`}
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">{mom.explanation}</p>
        </div>

        {/* 3-Month Projection */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-3.5 backdrop-blur-xs">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-indigo-200">Projected Revenue ({forecast.target_period})</span>
              <span className="text-[10px] font-medium bg-amber-400/20 text-amber-300 px-1.5 py-0.5 rounded">
                Estimated
              </span>
            </div>
            <span className="text-sm font-bold text-white">
              ₹{(forecast.forecast_amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 italic leading-snug">
            {forecast.disclaimer}
          </p>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-indigo-300">
        <span>Receivables: ₹{(data.outstanding_amount || 0).toLocaleString('en-IN')}</span>
        <span className="text-rose-300">Overdue: ₹{(data.overdue_amount || 0).toLocaleString('en-IN')}</span>
      </div>
    </div>
  )
}

