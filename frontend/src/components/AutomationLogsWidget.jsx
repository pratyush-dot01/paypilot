import { useState, useEffect } from 'react'
import { Activity, Play, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react'
import { getAutomationLogs, triggerAutomationJob } from '../services/api'

export default function AutomationLogsWidget() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [runningJob, setRunningJob] = useState(null)

  async function loadLogs() {
    try {
      const res = await getAutomationLogs(6)
      if (res && res.data) {
        setLogs(res.data)
      }
    } catch (err) {
      console.warn('Automation logs error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  async function handleRunNow(jobId) {
    setRunningJob(jobId)
    try {
      await triggerAutomationJob(jobId)
      await loadLogs()
    } catch (err) {
      console.error('Trigger job failed:', err)
    } finally {
      setRunningJob(null)
    }
  }

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold">
            <Activity size={18} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm">Background Task Execution Logs</h3>
            <p className="text-xs text-slate-500">APScheduler automation audit trail</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleRunNow('check_overdue_invoices')}
            disabled={runningJob !== null}
            className="text-[11px] font-medium text-slate-700 hover:text-indigo-600 bg-slate-50 hover:bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors flex items-center gap-1 disabled:opacity-50"
            title="Run Daily Overdue Check on demand"
          >
            <Play size={10} className={runningJob === 'check_overdue_invoices' ? 'animate-spin' : ''} />
            Run Overdue Check
          </button>
          <button
            onClick={loadLogs}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center py-6">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : logs.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-8 text-center text-slate-400">
          <Activity size={28} className="text-slate-300 mb-2" />
          <p className="text-xs font-medium text-slate-600">No automation logs yet</p>
          <p className="text-[11px] text-slate-400">Scheduled background jobs will log executions automatically.</p>
        </div>
      ) : (
        <div className="space-y-2 overflow-y-auto max-h-56 pr-1">
          {logs.map((log) => {
            const isSuccess = log.status === 'success'
            return (
              <div
                key={log.id}
                className="flex items-start justify-between p-2.5 rounded-xl bg-slate-50/80 border border-slate-100 hover:border-slate-200 transition-colors text-xs"
              >
                <div className="min-w-0 pr-2">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    {isSuccess ? (
                      <CheckCircle2 size={13} className="text-emerald-500 flex-shrink-0" />
                    ) : (
                      <AlertTriangle size={13} className="text-rose-500 flex-shrink-0" />
                    )}
                    <span className="font-semibold text-slate-800 truncate">{log.job_name}</span>
                    <span className="text-[10px] text-slate-400">({log.duration_ms}ms)</span>
                  </div>
                  <p className="text-[11px] text-slate-500 line-clamp-1">{log.summary}</p>
                </div>
                <span className="text-[10px] text-slate-400 flex-shrink-0 pt-0.5">
                  {new Date(log.executed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

