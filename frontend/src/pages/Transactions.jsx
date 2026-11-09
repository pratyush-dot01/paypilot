import { useState, useEffect } from 'react'
import Topbar from '../components/Topbar'
import { getTransactions } from '../services/api'
import { transactions as defaultTransactions } from '../data/mockData'
import { Download, Search, ArrowUpRight, ArrowDownLeft, ChevronLeft, ChevronRight } from 'lucide-react'

const statusConfig = {
  completed: { label: 'Completed', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pending: { label: 'Pending', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  failed: { label: 'Failed', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

const PAGE_SIZE = 8

export default function Transactions() {
  const [items, setItems] = useState(defaultTransactions)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  async function loadTransactions() {
    setLoading(true)
    try {
      const res = await getTransactions({
        status: statusFilter,
        type: typeFilter,
        search: search || undefined,
      })
      if (res && res.data && res.data.length > 0) {
        setItems(res.data)
      } else {
        setItems(defaultTransactions)
      }
    } catch (err) {
      console.warn('Transactions load fallback:', err)
      setItems(defaultTransactions)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTransactions()
  }, [statusFilter, typeFilter])

  const filtered = items.filter((t) => {
    const sLower = search.toLowerCase()
    const matchesSearch =
      (t.name || '').toLowerCase().includes(sLower) ||
      (t.id || '').toLowerCase().includes(sLower) ||
      (t.category || '').toLowerCase().includes(sLower)
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter
    const matchesType = typeFilter === 'all' || t.type === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="min-h-screen bg-slate-50">
      <Topbar title="Transactions" />
      <main className="p-6 space-y-5">

        {/* Filters row */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-48">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search by name, ID, or category..."
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="border border-slate-200 bg-white text-slate-700 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
            className="border border-slate-200 bg-white text-slate-700 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="all">All Types</option>
            <option value="credit">Credit</option>
            <option value="debit">Debit</option>
          </select>

          <button
            onClick={() => alert('Transactions export queued (CSV / Excel)')}
            className="flex items-center gap-2 bg-white border border-slate-200 text-slate-700 text-sm font-medium px-4 py-2.5 rounded-lg hover:bg-slate-50 transition-colors ml-auto"
          >
            <Download size={15} />
            Export
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50">
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-6 py-3">Transaction</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Category</th>
                  <th className="text-right text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Amount</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Date</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Status</th>
                  <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3">Type</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {paginated.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-400 text-sm">
                      No transactions found matching your criteria.
                    </td>
                  </tr>
                ) : (
                  paginated.map((txn) => {
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
                              <p className="text-slate-400 text-xs font-mono">{txn.id}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span className="text-slate-500 text-sm">{txn.category || 'Payment'}</span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <span className={`font-bold text-sm ${isCredit ? 'text-emerald-600' : 'text-rose-500'}`}>
                            {isCredit ? '+' : '-'}{formatCurrency(txn.amount)}
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
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
            <p className="text-slate-400 text-sm">
              Showing <span className="font-semibold text-slate-700">{filtered.length > 0 ? (page - 1) * PAGE_SIZE + 1 : 0}</span> to{' '}
              <span className="font-semibold text-slate-700">{Math.min(page * PAGE_SIZE, filtered.length)}</span> of{' '}
              <span className="font-semibold text-slate-700">{filtered.length}</span> results
            </p>
            <div className="flex items-center gap-1">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="p-2 text-slate-400 hover:text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg hover:bg-slate-100 transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                    page === p
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {p}
                </button>
              ))}
              <button
                disabled={page === totalPages || totalPages === 0}
                onClick={() => setPage((p) => p + 1)}
                className="p-2 text-slate-400 hover:text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg hover:bg-slate-100 transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>

      </main>
    </div>
  )
}
