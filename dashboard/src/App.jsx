import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Runs from './pages/Runs'
import RunDetail from './pages/RunDetail'

function Logo() {
  return (
    <span className="flex items-center gap-2.5 mr-8 shrink-0">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M12 2l1.8 4.6L18 8l-4.2 1.4L12 14l-1.8-4.6L6 8l4.2-1.4L12 2z" fill="#f5c518" />
        <path d="M18.5 14l1 2.6L22 17.5l-2.5.9-1 2.6-1-2.6-2.5-.9 2.5-.9 1-2.6z" fill="#4f8bff" />
      </svg>
      <span className="text-white font-bold text-sm tracking-tight">
        ACE<span className="text-brand-blue">-</span>BENCH
      </span>
    </span>
  )
}

function Nav() {
  const cls = ({ isActive }) =>
    `px-3.5 py-1.5 text-sm rounded-lg transition-colors ${isActive ? 'bg-brand-blue/15 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'}`
  return (
    <nav className="sticky top-0 z-20 backdrop-blur bg-ink-950/80 border-b border-white/5 flex items-center px-6 h-14">
      <Logo />
      <div className="flex items-center gap-1">
        <NavLink to="/" end className={cls}>Dashboard</NavLink>
        <NavLink to="/runs" className={cls}>Runs</NavLink>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-slate-200">
        <Nav />
        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/runs/:id" element={<RunDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
