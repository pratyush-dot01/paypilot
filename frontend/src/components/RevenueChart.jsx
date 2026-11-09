import { useState, useEffect } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getRevenueChart } from '../services/api'
import { monthlyRevenue as defaultData } from '../data/mockData'

function formatCurrency(value) {
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
  if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`
  return `₹${value}`
}

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 shadow-lg rounded-xl p-4">
        <p className="text-slate-700 font-semibold text-sm mb-2">{label} 2026</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
            <span className="text-slate-500 capitalize">{entry.name}:</span>
            <span className="font-semibold text-slate-800">{formatCurrency(entry.value)}</span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export default function RevenueChart() {
  const [data, setData] = useState(defaultData)

  useEffect(() => {
    let isMounted = true
    async function loadChart() {
      try {
        const chartData = await getRevenueChart()
        if (isMounted && chartData && chartData.length > 0) {
          setData(chartData)
        }
      } catch (err) {
        console.warn('Revenue chart fallback:', err)
      }
    }
    loadChart()
    return () => { isMounted = false }
  }, [])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-slate-900 font-bold text-base">Revenue vs Expenses</h2>
          <p className="text-slate-400 text-sm mt-0.5">12-month overview for 2026</p>
        </div>
        <div className="flex items-center gap-4 text-xs font-medium">
          <span className="flex items-center gap-1.5 text-slate-500">
            <span className="w-3 h-3 rounded bg-indigo-500" /> Revenue
          </span>
          <span className="flex items-center gap-1.5 text-slate-500">
            <span className="w-3 h-3 rounded bg-rose-400" /> Expenses
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#fb7185" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#fb7185" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tickFormatter={formatCurrency} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Area type="monotone" dataKey="revenue" name="revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#revenueGrad)" dot={false} activeDot={{ r: 5, fill: '#6366f1' }} />
          <Area type="monotone" dataKey="expenses" name="expenses" stroke="#fb7185" strokeWidth={2.5} fill="url(#expenseGrad)" dot={false} activeDot={{ r: 5, fill: '#fb7185' }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
