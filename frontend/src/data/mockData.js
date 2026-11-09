// Mock Data for PayPilot - Indian Fintech Sample Data

export const transactions = [
  { id: 'TXN001', name: 'Rahul Sharma', amount: 25000, date: '2024-01-15', status: 'completed', type: 'credit', category: 'Invoice Payment' },
  { id: 'TXN002', name: 'Priya Technologies Ltd', amount: 85000, date: '2024-01-14', status: 'completed', type: 'credit', category: 'Service Fee' },
  { id: 'TXN003', name: 'AWS India', amount: 12500, date: '2024-01-13', status: 'completed', type: 'debit', category: 'Cloud Services' },
  { id: 'TXN004', name: 'Infosys BPO', amount: 150000, date: '2024-01-12', status: 'pending', type: 'credit', category: 'Consulting' },
  { id: 'TXN005', name: 'Flipkart Seller', amount: 8750, date: '2024-01-11', status: 'completed', type: 'credit', category: 'Product Sale' },
  { id: 'TXN006', name: 'Google Workspace', amount: 4200, date: '2024-01-10', status: 'completed', type: 'debit', category: 'Software Subscription' },
  { id: 'TXN007', name: 'TCS Digital', amount: 200000, date: '2024-01-09', status: 'completed', type: 'credit', category: 'Project Payment' },
  { id: 'TXN008', name: 'Razorpay Gateway', amount: 3100, date: '2024-01-08', status: 'failed', type: 'debit', category: 'Transaction Fee' },
  { id: 'TXN009', name: 'Swiggy Business', amount: 6500, date: '2024-01-07', status: 'completed', type: 'debit', category: 'Office Meals' },
  { id: 'TXN010', name: 'Myntra Partners', amount: 42000, date: '2024-01-06', status: 'completed', type: 'credit', category: 'Partnership Revenue' },
  { id: 'TXN011', name: 'Jio Fiber Business', amount: 2999, date: '2024-01-05', status: 'completed', type: 'debit', category: 'Internet' },
  { id: 'TXN012', name: 'Accenture India', amount: 320000, date: '2024-01-04', status: 'pending', type: 'credit', category: 'Enterprise Contract' },
  { id: 'TXN013', name: 'Zoho Corporation', amount: 15000, date: '2024-01-03', status: 'completed', type: 'debit', category: 'CRM Subscription' },
  { id: 'TXN014', name: 'Nykaa Fashion', amount: 55000, date: '2024-01-02', status: 'completed', type: 'credit', category: 'Design Services' },
  { id: 'TXN015', name: 'PayTM Business', amount: 9800, date: '2024-01-01', status: 'failed', type: 'credit', category: 'Refund' },
  { id: 'TXN016', name: 'Meesho Supplier', amount: 18500, date: '2023-12-31', status: 'completed', type: 'credit', category: 'Product Sale' },
  { id: 'TXN017', name: 'Office Rent', amount: 45000, date: '2023-12-30', status: 'completed', type: 'debit', category: 'Rent' },
  { id: 'TXN018', name: 'Byju\'s EdTech', amount: 75000, date: '2023-12-29', status: 'completed', type: 'credit', category: 'Training Revenue' },
  { id: 'TXN019', name: 'HDFC Bank Charges', amount: 1250, date: '2023-12-28', status: 'completed', type: 'debit', category: 'Bank Charges' },
  { id: 'TXN020', name: 'Ola Corporate', amount: 12000, date: '2023-12-27', status: 'pending', type: 'credit', category: 'Transport Services' },
]

export const invoices = [
  { id: 'INV001', client: 'Infosys BPO Solutions', amount: 150000, dueDate: '2024-01-20', status: 'pending', invoiceNo: 'PP-2024-001' },
  { id: 'INV002', client: 'TCS Digital Services', amount: 200000, dueDate: '2024-01-15', status: 'paid', invoiceNo: 'PP-2024-002' },
  { id: 'INV003', client: 'Accenture India Pvt Ltd', amount: 320000, dueDate: '2024-01-10', status: 'overdue', invoiceNo: 'PP-2024-003' },
  { id: 'INV004', client: 'Priya Technologies Ltd', amount: 85000, dueDate: '2024-01-25', status: 'paid', invoiceNo: 'PP-2024-004' },
  { id: 'INV005', client: 'Myntra Fashion Pvt Ltd', amount: 55000, dueDate: '2024-02-01', status: 'pending', invoiceNo: 'PP-2024-005' },
  { id: 'INV006', client: 'Nykaa E-Retail Ltd', amount: 42000, dueDate: '2023-12-31', status: 'overdue', invoiceNo: 'PP-2023-098' },
  { id: 'INV007', client: 'Byju\'s Think & Learn', amount: 75000, dueDate: '2024-01-30', status: 'paid', invoiceNo: 'PP-2024-006' },
  { id: 'INV008', client: 'Ola Electric Mobility', amount: 12000, dueDate: '2024-02-05', status: 'pending', invoiceNo: 'PP-2024-007' },
  { id: 'INV009', client: 'Meesho Internet Pvt Ltd', amount: 18500, dueDate: '2023-12-15', status: 'overdue', invoiceNo: 'PP-2023-095' },
  { id: 'INV010', client: 'Rahul Sharma Consulting', amount: 25000, dueDate: '2024-01-28', status: 'paid', invoiceNo: 'PP-2024-008' },
]

export const monthlyRevenue = [
  { month: 'Jan', revenue: 420000, expenses: 185000 },
  { month: 'Feb', revenue: 380000, expenses: 162000 },
  { month: 'Mar', revenue: 510000, expenses: 198000 },
  { month: 'Apr', revenue: 475000, expenses: 210000 },
  { month: 'May', revenue: 620000, expenses: 225000 },
  { month: 'Jun', revenue: 580000, expenses: 195000 },
  { month: 'Jul', revenue: 695000, expenses: 240000 },
  { month: 'Aug', revenue: 720000, expenses: 258000 },
  { month: 'Sep', revenue: 650000, expenses: 230000 },
  { month: 'Oct', revenue: 780000, expenses: 275000 },
  { month: 'Nov', revenue: 840000, expenses: 290000 },
  { month: 'Dec', revenue: 920000, expenses: 310000 },
]

export const stats = {
  totalRevenue: 2847500,
  pendingPayments: 585500,
  completedTransactions: 847,
  overdueInvoices: 3,
}

export const expenseBreakdown = [
  { name: 'Cloud Services', value: 125000, color: '#6366f1' },
  { name: 'Salaries', value: 850000, color: '#8b5cf6' },
  { name: 'Marketing', value: 180000, color: '#a78bfa' },
  { name: 'Office & Rent', value: 540000, color: '#c4b5fd' },
  { name: 'Software Tools', value: 95000, color: '#ddd6fe' },
  { name: 'Others', value: 72000, color: '#ede9fe' },
]

export const transactionVolume = [
  { month: 'Jan', volume: 42 },
  { month: 'Feb', volume: 38 },
  { month: 'Mar', volume: 55 },
  { month: 'Apr', volume: 48 },
  { month: 'May', volume: 72 },
  { month: 'Jun', volume: 65 },
  { month: 'Jul', volume: 80 },
  { month: 'Aug', volume: 88 },
  { month: 'Sep', volume: 76 },
  { month: 'Oct', volume: 95 },
  { month: 'Nov', volume: 102 },
  { month: 'Dec', volume: 120 },
]
