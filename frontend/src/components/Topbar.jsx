import { Bell, Search, Menu } from 'lucide-react'
import { useNavigation } from '../context/NavigationContext'

export default function Topbar({ title }) {
  const { toggleMobile } = useNavigation()

  return (
    <header className="bg-white border-b border-slate-100 shadow-sm px-4 sm:px-6 py-4 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile Toggle + Page title */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobile}
          className="md:hidden p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
      </div>

      {/* Right: Search + Notifications + Avatar */}
      <div className="flex items-center gap-3">
        <div className="relative hidden sm:block">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search..."
            className="pl-9 pr-4 py-2 bg-slate-100 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:bg-white w-36 sm:w-52 transition-all"
          />
        </div>

        <button className="relative p-2.5 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full ring-2 ring-white" />
        </button>

        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center cursor-pointer">
          <span className="text-white text-sm font-semibold">PK</span>
        </div>
      </div>
    </header>
  )
}
