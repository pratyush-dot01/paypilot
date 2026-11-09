import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getRecentTransactions } from '../services/api'
import { transactions as mockTransactions } from '../data/mockData'
import { ArrowUpRight, ArrowDownLeft } from 'lucide-react'

const statusConfig = {
  completed: { label: 'Completed', cls: 'bg-emerald-50 text-emerald-700 border-emerald-100' },
  pending: { label: 'Pending', cls: 'bg-amber-50 text-amber-700 border-amber-100' },
  failed: { label: 'Failed', cls: 'bg-rose-50 text-rose-700 border-rose-100' },
}

function formatAmount(amount) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function RecentTransactions() {
  const [items, setItems] = useState(mockTransactions.slice(0, 7))

  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        const data = await getRecentTransactions()
        if (isMounted && data && data.length > 0) {
          setItems(data)
        }
      } catch (err) {
        console.warn('Recent transactions fallback:', err)
      }
    }
    loadData()
    return () => { isMounted = false }
  }, [])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100">
      <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
        <div>
          <h2 className="text-slate-900 font-bold text-base">Recent Transactions</h2>
          <p className="text-slate-400 text-sm mt-0.5">Last 7 transactions</p>
        </div>
        <Link to="/transactions" className="text-indigo-600 text-sm font-semibold hover:text-indigo-700 transition-colors">
          View All →
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-6 py-3">Transaction</th>
              <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Amount</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Date</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Status</th>
              <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Type</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {items.map((txn) => {
              const status = statusConfig[txn.status] || statusConfig.completed
              const isCredit = txn.type === 'credit'
              return (
                <tr key={txn.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isCredit ? 'bg-emerald-50' : 'bg-rose-50'
                      }`}>
                        {isCredit
                          ? <ArrowUpRight size={16} className="text-emerald-600" />
                          : <ArrowDownLeft size={16} className="text-rose-500" />
                        }
                      </div>
                      <div>
                        <p className="text-slate-800 font-semibold text-sm">{txn.name}</p>
                        <p className="text-slate-400 text-xs">{txn.category || 'Payment'} · {txn.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <span className={`font-bold text-sm ${isCredit ? 'text-emerald-600' : 'text-rose-500'}`}>
                      {isCredit ? '+' : '-'}{formatAmount(txn.amount)}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-slate-500 text-sm">{formatDate(txn.date || txn.created_date)}</span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${status.cls}`}>
                      {status.label}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`text-xs font-semibold capitalize ${isCredit ? 'text-emerald-600' : 'text-rose-500'}`}>
                      {txn.type}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
