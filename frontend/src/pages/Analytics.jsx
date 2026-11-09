import { useState, useEffect } from 'react'
import Topbar from '../components/Topbar'
import { getRevenueChart } from '../services/api'
import { monthlyRevenue as defaultMonthly, expenseBreakdown, transactionVolume } from '../data/mockData'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line
} from 'recharts'

function formatCurrency(value) {
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`
  if (value >= 1000) return `₹${(value / 1000).toFixed(0)}K`
  return `₹${value}`
}

function CustomBar({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 shadow-lg rounded-xl p-3 text-sm">
        <p className="font-semibold text-slate-700 mb-1">{label}</p>
        <p className="text-indigo-600">Revenue: {formatCurrency(payload[0]?.value)}</p>
      </div>
    )
  }
  return null
}

function CustomLine({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 shadow-lg rounded-xl p-3 text-sm">
        <p className="font-semibold text-slate-700 mb-1">{label}</p>
        <p className="text-indigo-600">Volume: {payload[0]?.value} txns</p>
      </div>
    )
  }
  return null
}

const DATE_RANGES = ['Last 3 months', 'Last 6 months', 'This year', 'All time']

export default function Analytics() {
  const [dateRange, setDateRange] = useState('This year')
  const [chartData, setChartData] = useState(defaultMonthly)

  useEffect(() => {
    let isMounted = true
    async function loadData() {
      try {
        const data = await getRevenueChart()
        if (isMounted && data && data.length > 0) {
          setChartData(data)
        }
      } catch (err) {
        console.warn('Analytics data fallback:', err)
      }
    }
    loadData()
    return () => { isMounted = false }
  }, [])

  const totalRevenue = chartData.reduce((s, m) => s + m.revenue, 0)
  const totalExpenses = chartData.reduce((s, m) => s + m.expenses, 0)
  const netProfit = totalRevenue - totalExpenses
  const margin = totalRevenue > 0 ? ((netProfit / totalRevenue) * 100).toFixed(1) : '0.0'

  return (
    <div className="min-h-screen bg-slate-50">
      <Topbar title="Analytics" />
      <main className="p-6 space-y-6">

        {/* Date range + Summary insights */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex gap-1 p-1 bg-white border border-slate-200 rounded-lg">
            {DATE_RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setDateRange(r)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  dateRange === r ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-4">
            {[
              { label: 'Total Revenue', value: formatCurrency(totalRevenue), color: 'text-indigo-600' },
              { label: 'Total Expenses', value: formatCurrency(totalExpenses), color: 'text-rose-500' },
              { label: 'Net Profit', value: formatCurrency(netProfit), color: 'text-emerald-600' },
              { label: 'Profit Margin', value: `${margin}%`, color: 'text-slate-800' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-white border border-slate-200 rounded-xl px-4 py-3 text-center">
                <p className="text-slate-400 text-xs mb-0.5">{label}</p>
                <p className={`text-base font-bold ${color}`}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Monthly Revenue Bar Chart */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Monthly Revenue Breakdown</h3>
              <p className="text-slate-400 text-sm">Revenue trends across months</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={formatCurrency} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomBar />} />
              <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Two-column charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

          {/* Expense Breakdown Donut */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="font-bold text-slate-900 text-base mb-1">Expense Breakdown</h3>
            <p className="text-slate-400 text-sm mb-4">By category</p>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={expenseBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={85}>
                  {expenseBreakdown.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value}%`} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Transaction Volume Line */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="font-bold text-slate-900 text-base mb-1">Transaction Volume</h3>
            <p className="text-slate-400 text-sm mb-4">Daily transaction count (last 7 days)</p>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={transactionVolume} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomLine />} />
                <Line type="monotone" dataKey="volume" stroke="#6366f1" strokeWidth={2.5} dot={{ fill: '#6366f1', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

        </div>

      </main>
    </div>
  )
}
