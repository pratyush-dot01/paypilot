import { FilePlus, BellRing, PlusCircle, Download } from 'lucide-react'

const actions = [
  { icon: FilePlus, label: 'Create Invoice', desc: 'New invoice', primary: true },
  { icon: BellRing, label: 'Send Reminder', desc: 'Payment nudge', primary: false },
  { icon: PlusCircle, label: 'Add Transaction', desc: 'Log manually', primary: false },
  { icon: Download, label: 'Export Report', desc: 'PDF / Excel', primary: false },
]

export default function QuickActions() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <h2 className="text-slate-900 font-bold text-base mb-4">Quick Actions</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {actions.map(({ icon: Icon, label, desc, primary }) => (
          <button
            key={label}
            className={`flex flex-col items-center gap-2.5 p-4 rounded-xl border-2 transition-all group cursor-pointer ${
              primary
                ? 'border-indigo-500 bg-indigo-500 text-white hover:bg-indigo-600 hover:border-indigo-600 shadow-md shadow-indigo-200'
                : 'border-slate-200 bg-white text-slate-700 hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-700'
            }`}
          >
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              primary ? 'bg-white/20' : 'bg-slate-100 group-hover:bg-indigo-100'
            }`}>
              <Icon size={20} className={primary ? 'text-white' : 'text-slate-600 group-hover:text-indigo-600'} />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm leading-tight">{label}</p>
              <p className={`text-xs mt-0.5 ${primary ? 'text-indigo-100' : 'text-slate-400'}`}>{desc}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
