import { TrendingUp, TrendingDown } from 'lucide-react'

const colorMap = {
  indigo: {
    bg: 'bg-indigo-50',
    icon: 'bg-indigo-500',
    text: 'text-indigo-600',
  },
  amber: {
    bg: 'bg-amber-50',
    icon: 'bg-amber-500',
    text: 'text-amber-600',
  },
  emerald: {
    bg: 'bg-emerald-50',
    icon: 'bg-emerald-500',
    text: 'text-emerald-600',
  },
  rose: {
    bg: 'bg-rose-50',
    icon: 'bg-rose-500',
    text: 'text-rose-600',
  },
}

export default function StatCard({ title, value, change, changeType, icon: Icon, color = 'indigo' }) {
  const colors = colorMap[color] || colorMap.indigo
  const isUp = changeType === 'up'

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-11 h-11 ${colors.icon} rounded-xl flex items-center justify-center shadow-sm`}>
          <Icon size={20} className="text-white" />
        </div>
        <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full ${
          isUp ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
        }`}>
          {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {change}
        </div>
      </div>
      <div>
        <p className="text-slate-500 text-sm font-medium mb-1">{title}</p>
        <p className="text-slate-900 text-2xl font-bold tracking-tight">{value}</p>
      </div>
    </div>
  )
}
