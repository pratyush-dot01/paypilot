import { useState } from 'react'
import Topbar from '../components/Topbar'
import { User, Building2, Bell, Key, Palette } from 'lucide-react'

function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-indigo-600' : 'bg-slate-300'}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  )
}

function SectionCard({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-100">
        <div className="w-9 h-9 bg-indigo-50 rounded-lg flex items-center justify-center">
          <Icon size={18} className="text-indigo-600" />
        </div>
        <h2 className="text-slate-900 font-bold text-base">{title}</h2>
      </div>
      <div className="p-6 space-y-5">{children}</div>
    </div>
  )
}

function FormField({ label, type = 'text', defaultValue, placeholder }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
      <input
        type={type}
        defaultValue={defaultValue}
        placeholder={placeholder}
        className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:bg-white transition-all"
      />
    </div>
  )
}

export default function Settings() {
  const [notifications, setNotifications] = useState({
    paymentReceived: true,
    invoiceOverdue: true,
    weeklyReport: false,
    aiInsights: true,
    failedTransactions: true,
  })
  const [appearance, setAppearance] = useState('light')

  return (
    <div className="min-h-screen bg-slate-50">
      <Topbar title="Settings" />
      <main className="p-6 space-y-6 max-w-3xl">

        {/* Profile */}
        <SectionCard icon={User} title="Profile">
          <div className="flex items-center gap-4 mb-5 pb-5 border-b border-slate-100">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center">
              <span className="text-white text-xl font-bold">PK</span>
            </div>
            <div>
              <p className="text-slate-900 font-semibold">Pratyush Kumar</p>
              <p className="text-slate-400 text-sm">pratyush@paypilot.in</p>
              <button className="text-indigo-600 text-sm font-medium mt-1 hover:text-indigo-700">Change photo</button>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="First Name" defaultValue="Pratyush" />
            <FormField label="Last Name" defaultValue="Kumar" />
            <FormField label="Email" type="email" defaultValue="pratyush@paypilot.in" />
            <FormField label="Phone" defaultValue="+91 98765 43210" />
          </div>
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors mt-2">Save Changes</button>
        </SectionCard>

        {/* Business Info */}
        <SectionCard icon={Building2} title="Business Information">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="Business Name" defaultValue="PayPilot Solutions Pvt. Ltd." />
            <FormField label="GSTIN" defaultValue="29AABCU9603R1ZX" />
            <FormField label="PAN" defaultValue="AABCU9603R" />
            <FormField label="Industry" defaultValue="Financial Technology" />
            <div className="sm:col-span-2">
              <FormField label="Business Address" defaultValue="123, Tech Park, Whitefield, Bengaluru - 560066" />
            </div>
          </div>
          <button className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors mt-2">Save Changes</button>
        </SectionCard>

        {/* Notifications */}
        <SectionCard icon={Bell} title="Notifications">
          <div className="space-y-4">
            {[
              { key: 'paymentReceived', label: 'Payment Received', desc: 'Get notified when a payment is received' },
              { key: 'invoiceOverdue', label: 'Invoice Overdue', desc: 'Alerts for overdue invoices' },
              { key: 'weeklyReport', label: 'Weekly Summary Report', desc: 'Receive a weekly financial summary' },
              { key: 'aiInsights', label: 'AI Insights', desc: 'AI-powered business insights and suggestions' },
              { key: 'failedTransactions', label: 'Failed Transactions', desc: 'Alerts for failed or declined transactions' },
            ].map(({ key, label, desc }) => (
              <div key={key} className="flex items-center justify-between py-2">
                <div>
                  <p className="text-slate-800 font-medium text-sm">{label}</p>
                  <p className="text-slate-400 text-xs mt-0.5">{desc}</p>
                </div>
                <Toggle
                  checked={notifications[key]}
                  onChange={(val) => setNotifications((prev) => ({ ...prev, [key]: val }))}
                />
              </div>
            ))}
          </div>
        </SectionCard>

        {/* API Keys */}
        <SectionCard icon={Key} title="API Keys">
          <div className="space-y-4">
            <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
              <strong>Note:</strong> API keys are managed securely via environment variables on the server. They are never exposed in this interface.
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">PayPal Mode</label>
              <input
                type="text"
                readOnly
                value="Sandbox (testing)"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">PayPal Mode</label>
              <input
                type="text"
                readOnly
                value="Sandbox (testing)"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Webhook URL</label>
              <input
                type="url"
                placeholder="https://your-domain.com/api/payments/webhook"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:bg-white transition-all"
              />
            </div>
            <button className="border border-indigo-200 text-indigo-600 hover:bg-indigo-50 text-sm font-semibold px-5 py-2.5 rounded-lg transition-colors">Configure Webhook</button>
          </div>
        </SectionCard>

        {/* Appearance */}
        <SectionCard icon={Palette} title="Appearance">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">Theme</label>
            <div className="flex gap-3">
              {['light', 'dark', 'system'].map((theme) => (
                <button
                  key={theme}
                  onClick={() => setAppearance(theme)}
                  className={`px-5 py-2.5 rounded-lg border-2 text-sm font-medium capitalize transition-all ${
                    appearance === theme
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
          </div>
        </SectionCard>

      </main>
    </div>
  )
}
