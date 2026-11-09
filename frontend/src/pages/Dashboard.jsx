import { useState, useEffect } from 'react'
import Topbar from '../components/Topbar'
import StatCard from '../components/StatCard'
import RevenueChart from '../components/RevenueChart'
import RecentTransactions from '../components/RecentTransactions'
import QuickActions from '../components/QuickActions'
import AnomalyAlerts from '../components/AnomalyAlerts'
import UpcomingDeadlines from '../components/UpcomingDeadlines'
import FinancialInsightsCard from '../components/FinancialInsightsCard'
import ReminderApprovalQueue from '../components/ReminderApprovalQueue'
import AutomationLogsWidget from '../components/AutomationLogsWidget'
import { getDashboardStats } from '../services/api'
import { stats as defaultStats } from '../data/mockData'
import { IndianRupee, Clock, CheckCircle, AlertCircle } from 'lucide-react'

function formatCurrency(amount) {
  if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)}L`
  }
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount)
}

export default function Dashboard() {
  const [dashboardStats, setDashboardStats] = useState(defaultStats)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let isMounted = true
    async function loadStats() {
      try {
        const data = await getDashboardStats()
        if (isMounted && data) {
          setDashboardStats(data)
        }
      } catch (err) {
        console.warn('Dashboard stats fallback:', err)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    loadStats()
    return () => { isMounted = false }
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      <Topbar title="Dashboard" />
      <main className="p-6 space-y-6">
        {/* Anomaly Alerts Banner */}
        <AnomalyAlerts />

        {/* Top KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard
            title="Total Revenue"
            value={formatCurrency(dashboardStats.totalRevenue)}
            change="+23.5%"
            changeType="up"
            icon={IndianRupee}
            color="indigo"
          />
          <StatCard
            title="Pending Payments"
            value={formatCurrency(dashboardStats.pendingPayments)}
            change="+4 new"
            changeType="down"
            icon={Clock}
            color="amber"
          />
          <StatCard
            title="Completed Transactions"
            value={dashboardStats.completedTransactions?.toLocaleString('en-IN') || '1,284'}
            change="+18.2%"
            changeType="up"
            icon={CheckCircle}
            color="emerald"
          />
          <StatCard
            title="Overdue Invoices"
            value={dashboardStats.overdueInvoices}
            change="-2 this week"
            changeType="down"
            icon={AlertCircle}
            color="rose"
          />
        </div>

        {/* Charts & Financial Insights */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2">
            <RevenueChart />
          </div>
          <div className="xl:col-span-1">
            <FinancialInsightsCard />
          </div>
        </div>

        {/* Automation Intelligence Row: Upcoming Deadlines & Reminder Queue */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <UpcomingDeadlines />
          <ReminderApprovalQueue />
        </div>

        {/* Bottom Row: Recent Transactions, Automation Logs & Quick Actions */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="xl:col-span-6">
            <RecentTransactions />
          </div>
          <div className="xl:col-span-4">
            <AutomationLogsWidget />
          </div>
          <div className="xl:col-span-2">
            <QuickActions />
          </div>
        </div>
      </main>
    </div>
  )
}
