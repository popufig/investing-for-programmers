import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { LayoutDashboard, Briefcase, TrendingUp, ShieldAlert, Eye, SlidersHorizontal, Lightbulb } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Holdings from './pages/Holdings'
import StockAnalysis from './pages/StockAnalysis'
import Compare from './pages/Compare'
import Watchlist from './pages/Watchlist'
import Screener from './pages/Screener'
import Risk from './pages/Risk'
import Thesis from './pages/Thesis'

const navItems = [
  { to: '/',        icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/holdings', icon: Briefcase,       label: 'Holdings'  },
  { to: '/watchlist', icon: Eye,            label: 'Watchlist' },
  { to: '/screener', icon: SlidersHorizontal, label: 'Screener' },
  { to: '/stocks',   icon: TrendingUp,      label: 'Analysis'  },
  { to: '/compare',  icon: TrendingUp,      label: 'Compare'   },
  { to: '/thesis',   icon: Lightbulb,       label: 'Thesis'    },
  { to: '/risk',     icon: ShieldAlert,     label: 'Risk'      },
]

function Sidebar() {
  return (
    <aside className="w-56 min-h-screen bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="px-5 py-6 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📈</span>
          <div>
            <p className="text-sm font-semibold text-slate-100 leading-tight">InvestIQ</p>
            <p className="text-xs text-slate-500">Analysis System</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-600">Not financial advice.</p>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/holdings" element={<Holdings />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/screener" element={<Screener />} />
            <Route path="/stocks" element={<StockAnalysis />} />
            <Route path="/stocks/:ticker" element={<StockAnalysis />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/thesis" element={<Thesis />} />
            <Route path="/thesis/:id" element={<Thesis />} />
            <Route path="/risk" element={<Risk />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
