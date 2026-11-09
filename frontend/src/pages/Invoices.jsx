import { useState, useEffect } from 'react'
import Topbar from '../components/Topbar'
import { getInvoices, getInvoiceSummary, createInvoice } from '../services/api'
import { invoices as defaultInvoices } from '../data/mockData'
import PayPalCheckoutModal from '../components/PayPalCheckoutModal'
import { FilePlus, Eye, Send, Download, X, CreditCard, CheckCircle2 } from 'lucide-react'

const tabs = ['All', 'Paid', 'Pending', 'Overdue']

const statusConfig = {
  paid: { label: 'Paid', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pending: { label: 'Pending', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  overdue: { label: 'Overdue', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
  draft: { label: 'Draft', cls: 'bg-slate-50 text-slate-700 border-slate-200' },
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount || 0)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Invoices() {
  const [activeTab, setActiveTab] = useState('All')
  const [invoiceList, setInvoiceList] = useState(defaultInvoices)
  const [summary, setSummary] = useState({ total: 0, paid: 0, pending: 0, overdue: 0 })
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [selectedInvoiceForPay, setSelectedInvoiceForPay] = useState(null)
  const [paymentSuccessToast, setPaymentSuccessToast] = useState(null)

  // New Invoice Form state
  const [newClient, setNewClient] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newAmount, setNewAmount] = useState('')
  const [newDueDate, setNewDueDate] = useState('')

  async function loadData() {
    setLoading(true)
    try {
      const statusParam = activeTab === 'All' ? undefined : activeTab.toLowerCase()
      const [invRes, sumRes] = await Promise.all([
        getInvoices({ status: statusParam }),
        getInvoiceSummary(),
      ])
      if (invRes && invRes.data) {
        setInvoiceList(invRes.data)
      }
      if (sumRes) {
        setSummary(sumRes)
      }
    } catch (err) {
      console.warn('Invoices data load fallback:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [activeTab])

  // Keyboard accessibility for modal dismissal
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setShowModal(false)
        setSelectedInvoiceForPay(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  async function handleCreateInvoice(e) {
    e.preventDefault()
    if (!newClient || !newAmount || !newDueDate) return
    setSubmitting(true)
    try {
      const amt = parseFloat(newAmount) || 1000
      await createInvoice({
        customer_id: 'cust_001',
        customer_name: newClient,
        description: newDesc || 'Consulting Services',
        items: [
          { description: newDesc || 'Professional Services', quantity: 1, unit_price: amt },
        ],
        tax_rate: 18.0,
        currency: 'INR',
        due_date: newDueDate,
        status: 'pending',
      })
      setShowModal(false)
      setNewClient('')
      setNewDesc('')
      setNewAmount('')
      setNewDueDate('')
      await loadData()
    } catch (err) {
      alert('Failed to create invoice: ' + (err.message || 'Error'))
    } finally {
      setSubmitting(false)
    }
  }

  function handlePaymentSuccess(captureResult) {
    setPaymentSuccessToast({
      message: `Invoice ${captureResult.invoice_number} successfully paid via PayPal!`,
      txnId: captureResult.transaction_id,
    })
    setTimeout(() => setPaymentSuccessToast(null), 6000)
    loadData()
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Topbar title="Invoices" />
      <main className="p-6 space-y-6">

        {/* Payment Success Toast */}
        {paymentSuccessToast && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-5 py-3 rounded-xl flex items-center justify-between shadow-sm animate-in fade-in duration-200">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 size={18} className="text-emerald-600" />
              <div>
                <p className="font-semibold text-sm">{paymentSuccessToast.message}</p>
                <p className="text-xs text-emerald-600 font-mono">Transaction ID: {paymentSuccessToast.txnId}</p>
              </div>
            </div>
            <button onClick={() => setPaymentSuccessToast(null)} className="text-emerald-600 hover:text-emerald-800">
              <X size={16} />
            </button>
          </div>
        )}

        {/* Summary Strip */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {[
            { label: 'Total Invoiced', value: summary.total || invoiceList.reduce((s, i) => s + (i.amount || i.total_amount || 0), 0), color: 'text-slate-800' },
            { label: 'Paid', value: summary.paid, color: 'text-emerald-600' },
            { label: 'Pending', value: summary.pending, color: 'text-amber-600' },
            { label: 'Overdue', value: summary.overdue, color: 'text-rose-600' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white rounded-xl border border-slate-100 shadow-sm p-4">
              <p className="text-slate-500 text-sm mb-1">{label}</p>
              <p className={`text-xl font-bold ${color}`}>{formatCurrency(value)}</p>
            </div>
          ))}
        </div>

        {/* Table Card */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100">
          <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-slate-100 rounded-lg">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                    activeTab === tab
                      ? 'bg-white text-slate-900 shadow-sm'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
            >
              <FilePlus size={15} />
              New Invoice
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50">
                  {['Invoice No.', 'Client', 'Amount', 'Due Date', 'Status', 'Payment & Actions'].map((h) => (
                    <th key={h} className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider px-6 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {invoiceList.map((inv) => {
                  const statusKey = (inv.status || 'pending').toLowerCase()
                  const st = statusConfig[statusKey] || statusConfig.pending
                  const invNo = inv.invoice_number || inv.invoiceNo || inv.id
                  const clientName = inv.customer_name || inv.client || 'Client'
                  const totalAmt = inv.total_amount ?? inv.amount ?? 0
                  const due = inv.due_date || inv.dueDate
                  const isPayable = statusKey === 'pending' || statusKey === 'overdue'

                  return (
                    <tr key={inv.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-mono text-sm text-indigo-600 font-semibold">{invNo}</span>
                      </td>
                      <td className="px-6 py-4">
                        <p className="text-slate-800 font-medium text-sm">{clientName}</p>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-slate-800 font-bold text-sm">{formatCurrency(totalAmt)}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-slate-500 text-sm">{formatDate(due)}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${st.cls}`}>
                          {st.label}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {isPayable ? (
                            <button
                              onClick={() => setSelectedInvoiceForPay(inv)}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#003087] hover:bg-[#002266] text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
                              title="Pay using PayPal Sandbox"
                            >
                              <CreditCard size={13} />
                              Pay Now
                            </button>
                          ) : (
                            <span className="text-xs font-medium text-emerald-600 flex items-center gap-1">
                              ✓ Paid
                            </span>
                          )}

                          <div className="flex items-center gap-1 border-l border-slate-200 pl-2">
                            <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="View Details">
                              <Eye size={15} />
                            </button>
                            <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Send Reminder">
                              <Send size={15} />
                            </button>
                            <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Download PDF">
                              <Download size={15} />
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* PayPal Checkout Modal */}
        {selectedInvoiceForPay && (
          <PayPalCheckoutModal
            invoice={selectedInvoiceForPay}
            onClose={() => setSelectedInvoiceForPay(null)}
            onPaymentSuccess={handlePaymentSuccess}
          />
        )}

        {/* Create Invoice Modal */}
        {showModal && (
          <div 
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={(e) => { if (e.target === e.currentTarget && !submitting) setShowModal(false); }}
          >
            <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-100 overflow-hidden">
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                <h3 className="font-bold text-slate-900 text-base">Create New Invoice</h3>
                <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                  <X size={18} />
                </button>
              </div>
              <form onSubmit={handleCreateInvoice} className="p-6 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Client Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Infosys BPO, Wipro Digital"
                    value={newClient}
                    onChange={(e) => setNewClient(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Description</label>
                  <input
                    type="text"
                    placeholder="e.g. Cloud Security Audit"
                    value={newDesc}
                    onChange={(e) => setNewDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Amount (₹)</label>
                    <input
                      type="number"
                      required
                      min="1"
                      step="0.01"
                      placeholder="50000"
                      value={newAmount}
                      onChange={(e) => setNewAmount(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-600 uppercase mb-1">Due Date</label>
                    <input
                      type="date"
                      required
                      value={newDueDate}
                      onChange={(e) => setNewDueDate(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 border border-slate-200 text-slate-600 rounded-lg text-sm font-semibold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting ? 'Generating...' : 'Create Invoice'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

      </main>
    </div>
  )
}
