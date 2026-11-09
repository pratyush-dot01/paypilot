import { useState, useEffect } from 'react'
import { CalendarClock, ArrowUpRight, CheckCircle2, Clock } from 'lucide-react'
import { getUpcomingDeadlines } from '../services/api'

export default function UpcomingDeadlines() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    async function load() {
      try {
        const res = await getUpcomingDeadlines(7)
        if (isMounted && res && res.data) {
          setInvoices(res.data)
        }
      } catch (err) {
        console.warn('Upcoming deadlines fallback:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    load()
    return () => { isMounted = false }
  }, [])

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <CalendarClock size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm">Upcoming Invoice Deadlines</h3>
            <p className="text-xs text-slate-500">Unpaid invoices due in the next 7 days</p>
          </div>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
          {invoices.length} Due Soon
        </span>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : invoices.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-8 text-center text-slate-400">
          <CheckCircle2 size={32} className="text-emerald-500 mb-2" />
          <p className="text-xs font-medium text-slate-700">All invoices on schedule!</p>
          <p className="text-[11px] text-slate-400">No pending deadlines in the next 7 days.</p>
        </div>
      ) : (
        <div className="space-y-2.5 overflow-y-auto max-h-60 pr-1">
          {invoices.slice(0, 5).map((inv) => {
            const amount = inv.total_amount || inv.amount || 0
            const daysLeft = inv.days_remaining ?? 'soon'
            return (
              <div
                key={inv.id || inv.invoice_number}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 hover:border-indigo-100 transition-colors"
              >
                <div className="min-w-0 pr-3">
                  <p className="text-xs font-semibold text-slate-900 truncate">
                    {inv.customer_name || inv.client || 'Client'}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-slate-400">{inv.invoice_number || inv.invoice_no}</span>
                    <span className="text-[11px] font-medium text-amber-600 flex items-center gap-1">
                      <Clock size={11} /> {typeof daysLeft === 'number' ? `in ${daysLeft}d` : daysLeft}
                    </span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-xs font-bold text-slate-900">
                    ₹{amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </p>
                  <span className="text-[10px] text-slate-400">Due {inv.due_date}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

