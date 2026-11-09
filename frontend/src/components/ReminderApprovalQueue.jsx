import { useState, useEffect } from 'react'
import { BellRing, Send, CheckCircle2, RefreshCw, AlertCircle } from 'lucide-react'
import { getReminders, approveAndSendReminder, generateReminderRecommendations } from '../services/api'

export default function ReminderApprovalQueue() {
  const [reminders, setReminders] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  async function loadReminders() {
    setLoading(true)
    try {
      const res = await getReminders({ status: 'pending_approval', limit: 10 })
      if (res && res.data) {
        setReminders(res.data)
      }
    } catch (err) {
      console.warn('Failed to load pending reminders:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReminders()
  }, [])

  async function handleApprove(remId) {
    setActionLoading(remId)
    try {
      const res = await approveAndSendReminder(remId, 'in_app')
      if (res && res.success) {
        setSuccessMsg(`Reminder for invoice ${res.reminder?.invoice_id} dispatched!`)
        setTimeout(() => setSuccessMsg(null), 4000)
        setReminders((prev) => prev.filter((r) => r.id !== remId))
      }
    } catch (err) {
      console.error('Approval failed:', err)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleGenerateBatch() {
    setActionLoading('batch')
    try {
      await generateReminderRecommendations(3, false)
      await loadReminders()
      setSuccessMsg('Scanned invoices and updated recommendation queue!')
      setTimeout(() => setSuccessMsg(null), 4000)
    } catch (err) {
      console.error('Batch generation failed:', err)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <BellRing size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm">Automated Reminder Queue</h3>
            <p className="text-xs text-slate-500">Human-in-the-loop review before dispatch</p>
          </div>
        </div>
        <button
          onClick={handleGenerateBatch}
          disabled={actionLoading === 'batch'}
          className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-indigo-100 hover:bg-indigo-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={12} className={actionLoading === 'batch' ? 'animate-spin' : ''} />
          Scan Invoices
        </button>
      </div>

      {successMsg && (
        <div className="mb-3 p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 size={14} className="text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center py-6">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : reminders.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-8 text-center text-slate-400">
          <CheckCircle2 size={32} className="text-emerald-500 mb-2" />
          <p className="text-xs font-medium text-slate-700">Reminder queue is empty</p>
          <p className="text-[11px] text-slate-400">Click 'Scan Invoices' to detect upcoming deadlines and overdue bills.</p>
        </div>
      ) : (
        <div className="space-y-3 overflow-y-auto max-h-64 pr-1">
          {reminders.map((r) => (
            <div
              key={r.id}
              className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors"
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-bold text-slate-900 truncate">
                  {r.customer_name || 'Customer'}
                </span>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md bg-amber-100 text-amber-800">
                  Pending Approval
                </span>
              </div>
              <p className="text-xs text-slate-600 italic bg-white p-2 rounded-lg border border-slate-100 mb-2.5 line-clamp-2">
                "{r.message}"
              </p>
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-slate-400">Invoice: {r.invoice_id}</span>
                <button
                  onClick={() => handleApprove(r.id)}
                  disabled={actionLoading === r.id}
                  className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5 shadow-2xs transition-colors disabled:opacity-50"
                >
                  <Send size={12} />
                  {actionLoading === r.id ? 'Sending...' : 'Approve & Send'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

