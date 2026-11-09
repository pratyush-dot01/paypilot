import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bot,
  Send,
  Sparkles,
  User,
  Trash2,
  FileText,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Wrench,
  CheckCircle2,
  ExternalLink,
  ShieldAlert,
  CreditCard,
  Clock,
  XCircle,
} from 'lucide-react'
import Topbar from '../components/Topbar'
import {
  sendAIChat,
  getAISuggestedPrompts,
  getAIStatus,
  clearAIConversationMessages,
} from '../services/api'

const GREETING = {
  id: 'greeting',
  role: 'ai',
  text: "Hello! I'm **PayPilot AI**, your autonomous financial agent. I can directly create invoices, generate PayPal payment links (with your confirmation), search customers, schedule reminders, and query live transaction ledgers.\n\nTry asking me to *\"Create an invoice for ₹10,000 for TechCorp and generate its payment link\"* or *\"Find overdue invoices and prepare reminders\"*.",
  timestamp: new Date(),
  intent: 'GENERAL_FINANCIAL_QUERY',
}

function formatTime(date) {
  if (!date) return ''
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

export default function AIAssistant() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState([GREETING])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [suggestedPrompts, setSuggestedPrompts] = useState([
    'Remind customers whose invoices are overdue',
    'Show invoices due this week',
    'Summarize my revenue this month',
    'Find customers with repeated late payments',
    'Create an invoice for ₹10,000 to TechCorp and generate its payment link',
  ])
  const [aiStatus, setAiStatus] = useState(null)
  const [, setErrorMsg] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Fetch status & dynamic suggestions on mount
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [statusData, promptsData] = await Promise.all([
          getAIStatus(),
          getAISuggestedPrompts(),
        ])
        setAiStatus(statusData)
        if (Array.isArray(promptsData) && promptsData.length > 0) {
          // Prepend tool action suggestions
          const defaultActions = [
            'Create an invoice for ₹10,000 to TechCorp and generate its payment link',
            'Find overdue invoices and prepare reminders',
          ]
          const merged = [...defaultActions, ...promptsData.filter(p => !defaultActions.includes(p))]
          setSuggestedPrompts(merged.slice(0, 5))
        }
      } catch (err) {
        console.error('Failed to load AI metadata:', err)
      }
    }
    loadInitialData()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  async function handleSend(text, confirmedAction = null) {
    const userMsg = text || inputValue.trim()
    if (!userMsg) return

    setInputValue('')
    setErrorMsg(null)
    const userMessage = {
      id: Date.now(),
      role: 'user',
      text: userMsg,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsTyping(true)

    try {
      const response = await sendAIChat(userMsg, conversationId, confirmedAction)

      // Store conversation session ID
      if (response.conversation_id) {
        setConversationId(response.conversation_id)
      }

      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: response.response,
        intent: response.intent,
        entities: response.entities,
        tools_executed: response.tools_executed || [],
        confirmation_required: response.confirmation_required,
        action_completed: response.action_completed,
        data_preview: response.data_preview,
        model_used: response.model_used,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      console.error('Chat error:', err)
      setErrorMsg('Failed to process your request. Please try again.')
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'ai',
          text: 'I encountered an issue executing this action. Please check server logs or try again.',
          timestamp: new Date(),
          isError: true,
        },
      ])
    } finally {
      setIsTyping(false)
    }
  }

  async function handleClearChat() {
    if (conversationId) {
      try {
        await clearAIConversationMessages(conversationId)
      } catch (e) {
        console.warn('Failed to clear conversation on server:', e)
      }
    }
    setMessages([GREETING])
    setConversationId(null)
    setErrorMsg(null)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Markdown renderer for bold, lists, and code
  function renderFormattedText(text) {
    if (!text) return null
    const lines = text.split('\n')

    return lines.map((line, idx) => {
      // Bullet point line
      const isBullet = line.trim().startsWith('•') || line.trim().startsWith('-')
      const cleanLine = isBullet ? line.replace(/^[•-]\s*/, '') : line

      // Blockquote line
      const isQuote = line.trim().startsWith('>')
      const cleanQuote = isQuote ? line.replace(/^>\s*/, '') : cleanLine

      // Parse bold & code
      const parts = cleanQuote.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g)

      const renderedParts = parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={i} className="font-semibold text-slate-900">
              {part.slice(2, -2)}
            </strong>
          )
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code key={i} className="bg-slate-100 text-indigo-700 px-1.5 py-0.5 rounded text-xs font-mono">
              {part.slice(1, -1)}
            </code>
          )
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return (
            <em key={i} className="italic text-slate-600">
              {part.slice(1, -1)}
            </em>
          )
        }
        return part
      })

      if (isQuote) {
        return (
          <div key={idx} className="border-l-2 border-indigo-400 pl-3 my-1.5 text-slate-700 italic text-xs bg-indigo-50/40 py-1 rounded-r">
            {renderedParts}
          </div>
        )
      }

      if (isBullet) {
        return (
          <div key={idx} className="flex items-start gap-2 my-1">
            <span className="text-indigo-500 font-bold leading-5">•</span>
            <div className="flex-1">{renderedParts}</div>
          </div>
        )
      }

      return (
        <p key={idx} className={line.trim() === '' ? 'h-2' : 'my-0.5'}>
          {renderedParts}
        </p>
      )
    })
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <Topbar title="AI Assistant" />

      {/* AI Assistant Context Header Bar */}
      <div className="bg-white border-b border-slate-200/80 px-6 py-2.5 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-slate-700">PayPilot Autonomous Agent</span>
          </div>
          <span className="text-slate-300">|</span>
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <ShieldCheck size={14} className="text-indigo-600" />
            <span>Tools & Sandbox Active</span>
          </div>
          {aiStatus && (
            <span className="hidden sm:inline-block text-[11px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full font-medium">
              {aiStatus.provider === 'openai' ? 'OpenAI GPT' : aiStatus.live_connectivity ? 'Gemini 1.5 Flash' : 'Hybrid Tool Engine'}
            </span>
          )}
        </div>

        <button
          onClick={handleClearChat}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-rose-600 px-2.5 py-1 rounded-lg hover:bg-rose-50 transition-colors"
          title="Reset conversation"
        >
          <Trash2 size={13} />
          <span>Clear Chat</span>
        </button>
      </div>

      {/* Chat Messages Scroll Container */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3.5 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            {/* Avatar */}
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 shadow-xs ${
                msg.role === 'ai'
                  ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white'
                  : 'bg-slate-800 text-white'
              }`}
            >
              {msg.role === 'ai' ? <Bot size={18} /> : <User size={18} />}
            </div>

            {/* Bubble & Rich Widgets */}
            <div className={`max-w-2xl ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1.5`}>
              <div
                className={`px-4.5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-xs ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-xs'
                    : msg.isError
                    ? 'bg-rose-50 text-rose-900 border border-rose-200 rounded-tl-xs'
                    : 'bg-white text-slate-800 border border-slate-200/80 rounded-tl-xs'
                }`}
              >
                {/* Tool Execution Indicator Pill */}
                {msg.tools_executed && msg.tools_executed.length > 0 && (
                  <div className="mb-2.5 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1">
                      <Wrench size={11} className="text-indigo-500" />
                      Tools Executed:
                    </span>
                    {msg.tools_executed.map((t, idx) => (
                      <span
                        key={idx}
                        className={`text-[11px] font-mono px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                          t.success
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}
                      >
                        {t.success ? <CheckCircle2 size={10} /> : <XCircle size={10} />}
                        {t.tool_name}
                      </span>
                    ))}
                  </div>
                )}

                {msg.role === 'user' ? msg.text : renderFormattedText(msg.text)}

                {/* SENSITIVE ACTION CONFIRMATION CARD (Phase 5) */}
                {msg.confirmation_required && (
                  <div className="mt-3.5 p-4 bg-amber-50/90 border border-amber-200 rounded-xl space-y-3 shadow-xs">
                    <div className="flex items-center gap-2 text-amber-900 font-semibold text-xs uppercase tracking-wider border-b border-amber-200/80 pb-2">
                      <ShieldAlert size={16} className="text-amber-600" />
                      <span>Confirmation Required: Generate PayPal Payment Order</span>
                    </div>

                    <p className="text-xs text-amber-950 leading-relaxed">
                      {msg.confirmation_required.description}
                    </p>

                    <div className="flex items-center gap-2 pt-1">
                      <button
                        onClick={() =>
                          handleSend('Yes, please generate the PayPal payment link.', {
                            action: msg.confirmation_required.action,
                            ...msg.confirmation_required.parameters,
                          })
                        }
                        className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
                      >
                        <CheckCircle2 size={13} />
                        <span>Confirm & Generate Link</span>
                      </button>
                      <button
                        onClick={() => handleSend('No, cancel this action.')}
                        className="px-3 py-1.5 bg-white hover:bg-amber-100 text-amber-800 border border-amber-300 rounded-lg text-xs font-medium transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* PAYPAL PAYMENT LINK CARD (Phase 5) */}
                {(msg.data_preview?.type === 'paypal_link' || msg.action_completed?.action === 'create_paypal_order') && (
                  <div className="mt-3.5 p-4 bg-gradient-to-br from-indigo-50 to-blue-50 border border-blue-200 rounded-xl space-y-3 shadow-xs text-slate-900">
                    <div className="flex items-center justify-between border-b border-blue-200/80 pb-2">
                      <div className="flex items-center gap-2">
                        <CreditCard size={16} className="text-blue-600" />
                        <span className="font-semibold text-xs text-blue-950 uppercase tracking-wider">
                          PayPal Sandbox Order Active
                        </span>
                      </div>
                      <span className="text-[11px] font-mono px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full font-medium">
                        {msg.data_preview?.order_id || msg.action_completed?.order_id}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 block text-[11px]">Invoice</span>
                        <span className="font-semibold text-slate-800">
                          {msg.data_preview?.invoice_number || msg.action_completed?.invoice_number}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[11px]">Amount</span>
                        <span className="font-bold text-indigo-950">
                          {msg.data_preview?.currency || 'INR'} {Number(msg.data_preview?.amount || msg.action_completed?.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-blue-200/80 flex items-center justify-between">
                      <span className="text-[11px] text-slate-500">
                        Customer approval required
                      </span>
                      {msg.data_preview?.approval_url && (
                        <a
                          href={msg.data_preview.approval_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
                        >
                          <span>Approve with PayPal</span>
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* INVOICE CREATION SUCCESS CARD (Phase 5) */}
                {(msg.data_preview?.type === 'invoice_created' || msg.action_completed?.action === 'create_invoice') && (
                  <div className="mt-3.5 p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2.5 text-slate-800">
                    <div className="flex items-center justify-between border-b border-emerald-200/80 pb-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 size={15} className="text-emerald-600" />
                        <span className="font-semibold text-xs text-emerald-950 uppercase tracking-wider">
                          Invoice Saved in Database
                        </span>
                      </div>
                      <span className="text-[11px] font-mono px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full font-medium">
                        {msg.data_preview?.invoice_number || msg.action_completed?.invoice_number}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-500 block text-[11px]">Client</span>
                        <span className="font-semibold text-slate-800">
                          {msg.data_preview?.customer_name || 'Customer'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[11px]">Total with Tax</span>
                        <span className="font-bold text-slate-900">
                          {msg.data_preview?.currency || 'INR'} {Number(msg.data_preview?.total || msg.action_completed?.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-emerald-200/80 flex items-center justify-between">
                      <button
                        onClick={() =>
                          handleSend(`Create a payment link for invoice ${msg.data_preview?.invoice_number || msg.action_completed?.invoice_number}`)
                        }
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                      >
                        <span>Generate Payment Link</span>
                        <ArrowRight size={12} />
                      </button>

                      <button
                        onClick={() => navigate('/invoices')}
                        className="px-2.5 py-1 bg-white hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-medium transition-colors"
                      >
                        View in Invoices
                      </button>
                    </div>
                  </div>
                )}

                {/* Structured Rich Widget: KPI Summary */}
                {msg.data_preview?.type === 'kpi_summary' && (
                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100">
                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-500 block font-medium">Revenue</span>
                      <span className="text-xs font-bold text-emerald-600">
                        ₹{Number(msg.data_preview.revenue).toLocaleString('en-IN')}
                      </span>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-500 block font-medium">Pending</span>
                      <span className="text-xs font-bold text-amber-600">
                        ₹{Number(msg.data_preview.pending).toLocaleString('en-IN')}
                      </span>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-500 block font-medium">Completed</span>
                      <span className="text-xs font-bold text-slate-800">
                        {msg.data_preview.transactions} txns
                      </span>
                    </div>
                    <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-500 block font-medium">Overdue</span>
                      <span className="text-xs font-bold text-rose-600">
                        {msg.data_preview.overdue}
                      </span>
                    </div>
                  </div>
                )}

                {/* Structured Rich Widget: Overdue Alert */}
                {msg.data_preview?.type === 'overdue_list' && (
                  <div className="mt-3 p-3 bg-rose-50/70 border border-rose-200/80 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <AlertTriangle size={18} className="text-rose-600" />
                      <div>
                        <span className="text-xs font-bold text-rose-950 block">
                          {msg.data_preview.count} Invoices Overdue
                        </span>
                        <span className="text-[11px] text-rose-700">
                          Totaling ₹{Number(msg.data_preview.total).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate('/invoices')}
                      className="text-xs font-semibold px-2.5 py-1 bg-white hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg transition-colors"
                    >
                      Inspect
                    </button>
                  </div>
                )}

                {/* Structured Rich Widget: Customer Profile */}
                {msg.data_preview?.type === 'customer_card' && (
                  <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                    <div className="flex items-center justify-between border-b border-slate-200 pb-1.5">
                      <span className="font-bold text-xs text-slate-800">
                        {msg.data_preview.customer.name}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {msg.data_preview.customer.email}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 space-y-1">
                      <span className="text-[11px] text-slate-400 block font-medium">Open Bills:</span>
                      {msg.data_preview.invoices.map((inv, idx) => (
                        <div key={idx} className="flex justify-between items-center py-0.5">
                          <span>{inv.invoice_number}</span>
                          <span className="font-semibold">₹{Number(inv.total_amount).toLocaleString('en-IN')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Timestamp & Intent metadata */}
              <div className="flex items-center gap-2 px-1">
                <span className="text-slate-400 text-[11px]">{formatTime(msg.timestamp)}</span>
                {msg.intent && msg.role === 'ai' && (
                  <span className="text-[10px] text-slate-400 font-mono">
                    [{msg.intent.toLowerCase().replace(/_/g, ' ')}]
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center flex-shrink-0 shadow-xs text-white">
              <Bot size={18} />
            </div>
            <div className="bg-white border border-slate-200/80 shadow-xs rounded-2xl rounded-tl-xs px-4 py-3 flex items-center gap-2">
              <div className="flex gap-1.5 items-center">
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-slate-400 font-medium ml-1">Selecting tools & executing operations...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested Prompts + Input Tray */}
      <div className="bg-white border-t border-slate-200/80 px-6 pt-3.5 pb-5 space-y-3">
        {/* Dynamic prompt suggestion pills */}
        <div className="flex gap-2 flex-wrap items-center">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Sparkles size={11} className="text-indigo-500" />
            Agent Actions:
          </span>
          {suggestedPrompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => handleSend(prompt)}
              className="flex items-center gap-1 px-3 py-1 bg-indigo-50/80 text-indigo-700 text-xs font-medium rounded-full hover:bg-indigo-100 hover:text-indigo-800 transition-colors border border-indigo-100/90 shadow-2xs"
            >
              <span>{prompt}</span>
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask to create invoices, generate payment links, find overdue bills, or query ledgers..."
            className="flex-1 resize-none bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all max-h-32"
          />
          <button
            onClick={() => handleSend()}
            disabled={!inputValue.trim() || isTyping}
            className="w-11 h-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed text-white shadow-xs transition-colors flex-shrink-0"
            title="Send request"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
