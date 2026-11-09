import { useState, useEffect } from 'react'
import { PayPalScriptProvider, PayPalButtons } from '@paypal/react-paypal-js'
import { getPayPalConfig, createPayPalOrder, capturePayPalOrder } from '../services/api'
import { X, CheckCircle2, AlertCircle, Loader2, ShieldCheck, CreditCard } from 'lucide-react'

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount || 0)
}

export default function PayPalCheckoutModal({ invoice, onClose, onPaymentSuccess }) {
  const [config, setConfig] = useState(null)
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [processing, setProcessing] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)
  const [successData, setSuccessData] = useState(null)
  const [activeTab, setActiveTab] = useState('sdk') // 'sdk' or 'sandbox_demo'

  useEffect(() => {
    let isMounted = true
    async function fetchConfig() {
      try {
        const cfg = await getPayPalConfig()
        if (isMounted) setConfig(cfg)
      } catch (err) {
        console.warn('Failed to fetch PayPal config, using sandbox defaults:', err)
      } finally {
        if (isMounted) setLoadingConfig(false)
      }
    }
    fetchConfig()
    return () => { isMounted = false }
  }, [])

  // Keyboard accessibility: Escape key to close modal
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && !processing) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [processing, onClose])

  const totalAmount = invoice.total_amount ?? invoice.amount ?? 0
  const usdAmount = (totalAmount / 85.0).toFixed(2)

  // Standard PayPal SDK createOrder callback
  async function handleCreateOrder() {
    setErrorMsg(null)
    try {
      const res = await createPayPalOrder(invoice.id)
      return res.order_id
    } catch (err) {
      setErrorMsg(err.message || 'Failed to initiate PayPal order')
      throw err
    }
  }

  // Standard PayPal SDK onApprove callback
  async function handleApprove(data) {
    setProcessing(true)
    setErrorMsg(null)
    try {
      const captureRes = await capturePayPalOrder(data.orderID, invoice.id)
      setSuccessData(captureRes)
      if (onPaymentSuccess) {
        onPaymentSuccess(captureRes)
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to capture PayPal payment')
    } finally {
      setProcessing(false)
    }
  }

  // Fast sandbox direct capture simulation for automated demos
  async function handleOneClickSandboxCapture() {
    setProcessing(true)
    setErrorMsg(null)
    try {
      // 1. Create order
      const orderRes = await createPayPalOrder(invoice.id)
      // 2. Capture order (simulating approval for test order)
      const testOrderId = `TEST_${orderRes.order_id}`
      const captureRes = await capturePayPalOrder(testOrderId, invoice.id)
      setSuccessData(captureRes)
      if (onPaymentSuccess) {
        onPaymentSuccess(captureRes)
      }
    } catch (err) {
      setErrorMsg(err.message || 'Sandbox simulated capture failed')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !processing) onClose(); }}
    >
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#003087] flex items-center justify-center text-white font-bold text-sm tracking-tight shadow-sm">
              P
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base leading-tight">PayPal Checkout</h3>
              <p className="text-slate-500 text-xs font-mono">{invoice.invoice_number || invoice.invoiceNo}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5">

          {/* Success Screen */}
          {successData ? (
            <div className="text-center py-4 space-y-4">
              <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
                <CheckCircle2 size={36} />
              </div>
              <div>
                <h4 className="text-xl font-bold text-slate-900">Payment Completed!</h4>
                <p className="text-slate-500 text-sm mt-1">Invoice has been paid and verified via PayPal Sandbox</p>
              </div>

              <div className="bg-slate-50 rounded-xl p-4 text-left space-y-2 border border-slate-100 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Transaction ID:</span>
                  <span className="font-mono font-semibold text-slate-800">{successData.transaction_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">PayPal Order ID:</span>
                  <span className="font-mono text-slate-800">{successData.paypal_order_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">PayPal Capture ID:</span>
                  <span className="font-mono text-slate-800">{successData.paypal_capture_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Amount Paid:</span>
                  <span className="font-bold text-emerald-600 text-sm">{formatCurrency(totalAmount)} (~${usdAmount} USD)</span>
                </div>
                {successData.payer_email && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Payer:</span>
                    <span className="text-slate-800">{successData.payer_email}</span>
                  </div>
                )}
              </div>

              <button
                onClick={onClose}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 rounded-xl transition-colors shadow-sm"
              >
                Close & View Invoices
              </button>
            </div>
          ) : (
            <>
              {/* Order Breakdown Card */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2.5">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500">Client / Payee:</span>
                  <span className="font-semibold text-slate-800">{invoice.customer_name || invoice.client || 'Client'}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-500">Description:</span>
                  <span className="text-slate-700 truncate max-w-[240px]">{invoice.description || 'Professional Services'}</span>
                </div>
                <div className="pt-2 border-t border-slate-200/60 flex justify-between items-baseline">
                  <div>
                    <span className="text-slate-600 font-medium text-sm">Total Amount:</span>
                    <p className="text-slate-400 text-xs">Converted to USD for PayPal</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-bold text-slate-900">{formatCurrency(totalAmount)}</span>
                    <span className="block text-xs font-semibold text-indigo-600 font-mono">≈ ${usdAmount} USD</span>
                  </div>
                </div>
              </div>

              {/* Error Alert */}
              {errorMsg && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-xs text-rose-700">
                  <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Payment Error</p>
                    <p className="mt-0.5">{errorMsg}</p>
                  </div>
                </div>
              )}

              {/* Processing Spinner */}
              {processing && (
                <div className="py-6 text-center space-y-2">
                  <Loader2 size={32} className="animate-spin text-indigo-600 mx-auto" />
                  <p className="text-sm font-semibold text-slate-700">Capturing PayPal Payment...</p>
                  <p className="text-xs text-slate-400">Verifying transaction integrity and synchronizing database</p>
                </div>
              )}

              {/* PayPal Payment Methods */}
              {!processing && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-500 px-1">
                    <span>PAYPAL SANDBOX PAYMENT</span>
                    <span className="flex items-center gap-1 text-emerald-600">
                      <ShieldCheck size={14} /> Encrypted & Verified
                    </span>
                  </div>

                  {loadingConfig ? (
                    <div className="py-8 flex justify-center items-center">
                      <Loader2 size={24} className="animate-spin text-slate-400" />
                    </div>
                  ) : config?.client_id ? (
                    <div className="min-h-[120px] rounded-xl overflow-hidden p-1 bg-white border border-slate-100 shadow-sm">
                      <PayPalScriptProvider
                        options={{
                          clientId: config.client_id,
                          currency: 'USD',
                          intent: 'capture',
                          components: 'buttons',
                        }}
                      >
                        <PayPalButtons
                          style={{
                            layout: 'vertical',
                            color: 'gold',
                            shape: 'rect',
                            label: 'pay',
                            height: 42,
                          }}
                          createOrder={handleCreateOrder}
                          onApprove={handleApprove}
                          onError={(err) => {
                            console.error('PayPal Buttons error:', err)
                            setErrorMsg('PayPal checkout window encountered an error or was closed.')
                          }}
                          onCancel={() => {
                            setErrorMsg('Payment cancelled by customer.')
                          }}
                        />
                      </PayPalScriptProvider>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-xs text-slate-400">
                      PayPal client ID not available.
                    </div>
                  )}

                  {/* One-Click Fast Sandbox Capture for developer testing */}
                  <div className="pt-2 border-t border-slate-100">
                    <button
                      onClick={handleOneClickSandboxCapture}
                      disabled={processing}
                      className="w-full flex items-center justify-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold py-2.5 rounded-xl transition-all shadow-sm"
                    >
                      <CreditCard size={14} />
                      Simulate Sandbox Instant Approval (Test Flow)
                    </button>
                    <p className="text-[11px] text-slate-400 text-center mt-1.5">
                      Fast test approval without requiring external PayPal popup credentials
                    </p>
                  </div>
                </div>
              )}
            </>
          )}

        </div>

      </div>
    </div>
  )
}

