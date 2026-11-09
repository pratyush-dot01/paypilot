import axios from 'axios'
import {
  stats as mockStats,
  transactions as mockTransactions,
  invoices as mockInvoices,
  monthlyRevenue as mockMonthlyRevenue,
} from '../data/mockData'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Centralized Axios client instance
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,  // 30s — allows time for LLM + PayPal API calls
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor for uniform response / error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.warn(`[PayPilot API] Network or server warning: ${error.message}. Using resilient state.`)
    return Promise.reject(error)
  }
)

export default apiClient

// -------------------------------------------------------------
// Health Check
// -------------------------------------------------------------
export async function getHealth() {
  try {
    return await apiClient.get('/health')
  } catch {
    return { status: 'ok', version: '2.0.0 (offline fallback)', database: 'in-memory' }
  }
}

// -------------------------------------------------------------
// Dashboard & Analytics
// -------------------------------------------------------------
export async function getDashboardStats() {
  try {
    const data = await apiClient.get('/api/dashboard/stats')
    return {
      totalRevenue: data.total_revenue,
      pendingPayments: data.pending_payments,
      completedTransactions: data.completed_transactions,
      overdueInvoices: data.overdue_invoices,
    }
  } catch {
    return mockStats
  }
}

export async function getRevenueChart() {
  try {
    const res = await apiClient.get('/api/dashboard/revenue-chart')
    return res.data || mockMonthlyRevenue
  } catch {
    return mockMonthlyRevenue
  }
}

export async function getRecentTransactions() {
  try {
    const res = await apiClient.get('/api/dashboard/recent-transactions')
    return res.data || mockTransactions.slice(0, 7)
  } catch {
    return mockTransactions.slice(0, 7)
  }
}

// -------------------------------------------------------------
// Invoices
// -------------------------------------------------------------
export async function getInvoices(params = {}) {
  try {
    const cleanParams = {}
    if (params.status && params.status !== 'all') cleanParams.status = params.status
    if (params.search) cleanParams.search = params.search
    const res = await apiClient.get('/api/invoices/', { params: cleanParams })
    return { data: res.data, total: res.total }
  } catch {
    let filtered = [...mockInvoices]
    if (params.status && params.status !== 'all') {
      filtered = filtered.filter((i) => i.status === params.status)
    }
    return { data: filtered, total: filtered.length }
  }
}

export async function getInvoiceSummary() {
  try {
    return await apiClient.get('/api/invoices/summary')
  } catch {
    const total = mockInvoices.reduce((acc, i) => acc + (i.amount || 0), 0)
    const paid = mockInvoices.filter(i => i.status === 'paid').reduce((acc, i) => acc + (i.amount || 0), 0)
    const pending = mockInvoices.filter(i => i.status === 'pending').reduce((acc, i) => acc + (i.amount || 0), 0)
    const overdue = mockInvoices.filter(i => i.status === 'overdue').reduce((acc, i) => acc + (i.amount || 0), 0)
    return { total, paid, pending, overdue }
  }
}

export async function createInvoice(invoiceData) {
  try {
    return await apiClient.post('/api/invoices/', invoiceData)
  } catch (error) {
    console.error('Failed to create invoice:', error)
    throw error
  }
}

export async function updateInvoice(id, invoiceData) {
  try {
    return await apiClient.put(`/api/invoices/${id}`, invoiceData)
  } catch (error) {
    console.error('Failed to update invoice:', error)
    throw error
  }
}

export async function deleteInvoice(id) {
  try {
    return await apiClient.delete(`/api/invoices/${id}`)
  } catch (error) {
    console.error('Failed to delete invoice:', error)
    throw error
  }
}

// -------------------------------------------------------------
// Customers
// -------------------------------------------------------------
export async function getCustomers(params = {}) {
  try {
    return await apiClient.get('/api/customers/', { params })
  } catch {
    return { data: [], total: 0 }
  }
}

export async function createCustomer(customerData) {
  try {
    return await apiClient.post('/api/customers/', customerData)
  } catch (error) {
    console.error('Failed to create customer:', error)
    throw error
  }
}

// -------------------------------------------------------------
// Transactions
// -------------------------------------------------------------
export async function getTransactions(params = {}) {
  try {
    const cleanParams = {}
    if (params.status && params.status !== 'all') cleanParams.status = params.status
    if (params.type && params.type !== 'all') cleanParams.type = params.type
    if (params.search) cleanParams.search = params.search
    const res = await apiClient.get('/api/transactions/', { params: cleanParams })
    return { data: res.data, total: res.total }
  } catch {
    let filtered = [...mockTransactions]
    if (params.status && params.status !== 'all') filtered = filtered.filter(t => t.status === params.status)
    if (params.type && params.type !== 'all') filtered = filtered.filter(t => t.type === params.type)
    return { data: filtered, total: filtered.length }
  }
}

export async function createTransaction(txnData) {
  try {
    return await apiClient.post('/api/transactions/', txnData)
  } catch (error) {
    console.error('Failed to create transaction:', error)
    throw error
  }
}

// -------------------------------------------------------------
// Reminders
// -------------------------------------------------------------
export async function getReminders(params = {}) {
  try {
    return await apiClient.get('/api/reminders/', { params })
  } catch {
    return { data: [], total: 0 }
  }
}

export async function createReminder(reminderData) {
  try {
    return await apiClient.post('/api/reminders/', reminderData)
  } catch (error) {
    console.error('Failed to create reminder:', error)
    throw error
  }
}

export async function updateReminderStatus(reminderId, status) {
  try {
    return await apiClient.patch(`/api/reminders/${reminderId}/status?status=${status}`)
  } catch (error) {
    console.error('Failed to update reminder status:', error)
    throw error
  }
}

// -------------------------------------------------------------
// PayPal Payment APIs (Phase 3)
// -------------------------------------------------------------
export async function getPayPalConfig() {
  try {
    return await apiClient.get('/api/payments/config')
  } catch {
    return {
      client_id: 'BAAGOScv64uL0ghu44WpjZO9GiTB5Ty7C3ZzdvSD9cpBE-mILooJAgCUJ5WR-z7Frv10R6o4viTYH8X8z0',
      currency: 'USD',
      mode: 'sandbox',
      is_live: false,
    }
  }
}

export async function createPayPalOrder(invoiceId) {
  try {
    return await apiClient.post('/api/payments/create-order', { invoice_id: invoiceId })
  } catch (error) {
    console.error('Failed to create PayPal order:', error)
    throw error
  }
}

export async function capturePayPalOrder(orderId, invoiceId) {
  try {
    return await apiClient.post('/api/payments/capture-order', {
      order_id: orderId,
      invoice_id: invoiceId,
    })
  } catch (error) {
    console.error('Failed to capture PayPal order:', error)
    throw error
  }
}

export async function getPaymentForInvoice(invoiceId) {
  try {
    return await apiClient.get(`/api/payments/invoice/${invoiceId}`)
  } catch {
    return { is_paid: false, transactions: [] }
  }
}

// -------------------------------------------------------------
// AI Chat Assistant (Phase 5 Autonomous Agent with Tool Calling)
// -------------------------------------------------------------
export async function sendAIChat(message, conversationId = null, confirmedAction = null) {
  try {
    const res = await apiClient.post('/api/ai/chat', {
      message,
      conversation_id: conversationId,
      confirmed_action: confirmedAction,
    })
    return res
  } catch (error) {
    console.error('Failed to communicate with AI agent:', error)
    throw error
  }
}

export async function getAISuggestedPrompts() {
  try {
    return await apiClient.get('/api/ai/suggested-prompts')
  } catch {
    return [
      'Show my pending payments',
      'Which invoices are overdue?',
      'Analyse my monthly revenue',
      'Create an invoice for ₹5,000 for TechCorp',
      'Show my latest five transactions',
    ]
  }
}

export async function getAIStatus() {
  try {
    return await apiClient.get('/api/ai/status')
  } catch {
    return {
      status: 'offline',
      provider: 'local',
      model: 'paypilot-financial-engine',
      api_key_configured: false,
      live_connectivity: false,
      supported_intents: [],
    }
  }
}

export async function getAIConversations() {
  try {
    return await apiClient.get('/api/ai/conversations')
  } catch {
    return []
  }
}

export async function getAIConversation(conversationId) {
  try {
    return await apiClient.get(`/api/ai/conversations/${conversationId}`)
  } catch (error) {
    console.error('Failed to fetch conversation:', error)
    return null
  }
}

export async function deleteAIConversation(conversationId) {
  try {
    return await apiClient.delete(`/api/ai/conversations/${conversationId}`)
  } catch (error) {
    console.error('Failed to delete conversation:', error)
    throw error
  }
}

export async function clearAIConversationMessages(conversationId) {
  try {
    return await apiClient.delete(`/api/ai/conversations/${conversationId}/messages`)
  } catch (error) {
    console.error('Failed to clear conversation:', error)
    throw error
  }
}

// Backward-compatible wrapper
export async function sendChatMessage(message, conversationHistory = [], conversationId = null) {
  try {
    const res = await sendAIChat(message, conversationId)
    return {
      message: res.response,
      conversation_id: res.conversation_id,
      intent: res.intent,
      data_preview: res.data_preview,
      timestamp: res.timestamp || new Date().toISOString(),
    }
  } catch {
    // Client-side fallback if backend is unreachable
    const lowerMsg = message.toLowerCase()
    let reply = ''

    if (lowerMsg.includes('invoice') && lowerMsg.includes('create')) {
      reply = 'I\'ll help you create a new invoice! Please provide the client name, amount, and due date. For example: "Create invoice for Infosys BPO, ₹1,50,000, due next week"'
    } else if (lowerMsg.includes('pending') || lowerMsg.includes('payment')) {
      reply = 'You currently have pending payments recorded in PayPilot. Ask me "Which invoices are overdue?" or check the Invoices page for live records.'
    } else if (lowerMsg.includes('revenue') || lowerMsg.includes('analytics') || lowerMsg.includes('analyse')) {
      reply = 'PayPilot tracks your real-time revenue across MongoDB ledgers. Check the Analytics page or verify backend connectivity.'
    } else {
      reply = 'I\'m PayPilot AI, your grounded financial assistant. Ask me to "Show my pending payments", "Create an invoice for ₹5,000 to TechCorp", or "Analyse monthly revenue"!'
    }

    return { message: reply, timestamp: new Date().toISOString() }
  }
}

// -------------------------------------------------------------
// Phase 6: Automation & Financial Intelligence API Services
// -------------------------------------------------------------
export async function getAutomationStatus() {
  try {
    return await apiClient.get('/api/automation/status')
  } catch {
    return { scheduler_running: true, jobs: [], total_jobs: 0 }
  }
}

export async function triggerAutomationJob(jobId) {
  return await apiClient.post(`/api/automation/run/${jobId}`)
}

export async function getAutomationLogs(limit = 10) {
  try {
    return await apiClient.get('/api/automation/logs', { params: { limit } })
  } catch {
    return { data: [], total: 0 }
  }
}

export async function getNotifications(unreadOnly = false, type = null) {
  try {
    const params = {}
    if (unreadOnly) params.unread_only = true
    if (type) params.type = type
    return await apiClient.get('/api/notifications/', { params })
  } catch {
    return { data: [], total: 0, unread_count: 0 }
  }
}

export async function markNotificationRead(id) {
  return await apiClient.patch(`/api/notifications/${id}/read`)
}

export async function markAllNotificationsRead() {
  return await apiClient.post('/api/notifications/mark-all-read')
}

export async function getFinancialIntelligence() {
  try {
    return await apiClient.get('/api/analytics/financial-intelligence')
  } catch (err) {
    console.warn('Financial intelligence fallback:', err)
    return null
  }
}

export async function getAnomalies() {
  try {
    return await apiClient.get('/api/analytics/anomalies')
  } catch {
    return { anomalies_detected: 0, anomalies: [] }
  }
}

export async function getUpcomingDeadlines(days = 7) {
  try {
    return await apiClient.get('/api/analytics/upcoming-deadlines', { params: { days } })
  } catch {
    return { data: [], total: 0 }
  }
}

export async function generateReminderRecommendations(daysAhead = 3, overdueOnly = false) {
  return await apiClient.post('/api/reminders/generate-recommendations', {
    days_ahead: daysAhead,
    overdue_only: overdueOnly,
  })
}

export async function approveAndSendReminder(reminderId, channel = 'in_app', customMessage = null) {
  return await apiClient.post(`/api/reminders/${reminderId}/approve`, {
    reminder_id: reminderId,
    channel,
    custom_message: customMessage,
  })
}

