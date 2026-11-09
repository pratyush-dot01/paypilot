import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { NavigationProvider } from './context/NavigationContext'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import AIAssistant from './pages/AIAssistant'
import Invoices from './pages/Invoices'
import Transactions from './pages/Transactions'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

function App() {
  return (
    <NavigationProvider>
      <BrowserRouter>
        <div className="flex h-screen bg-slate-50 overflow-hidden">
          <Sidebar />
          <div className="flex-1 overflow-auto md:ml-64 w-full">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/ai" element={<AIAssistant />} />
              <Route path="/invoices" element={<Invoices />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </div>
      </BrowserRouter>
    </NavigationProvider>
  )
}

export default App
