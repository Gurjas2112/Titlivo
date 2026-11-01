import { NavLink, Outlet } from 'react-router'

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <svg viewBox="0 0 64 64" className="h-8 w-8" aria-hidden>
        <rect width="64" height="64" rx="14" fill={light ? '#ffffff' : '#0B1736'} />
        <path d="M14 46 L32 14 L50 46 Z" fill="none" stroke="#2EC4A6" strokeWidth="5" strokeLinejoin="round" />
        <circle cx="32" cy="36" r="6" fill="#FF7A00" />
      </svg>
      <span className={`text-lg font-bold tracking-tight ${light ? 'text-white' : 'text-navy'}`}>Titlivo</span>
    </span>
  )
}

const nav = [
  ['/', 'Search'],
  ['/verify', 'Verify a passport'],
  ['/developers', 'Developers'],
  ['/admin', 'Admin demo'],
] as const

export default function Layout() {
  return (
    <div className="flex min-h-full flex-col">
      <div className="bg-saffron px-4 py-1 text-center text-xs font-semibold text-white" data-testid="synthetic-ribbon">
        Synthetic data · prototype · not a legal opinion or a certified record
      </div>
      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <NavLink to="/" aria-label="Titlivo home">
            <Logo light />
          </NavLink>
          <nav className="flex flex-wrap gap-1 text-sm">
            {nav.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 font-medium transition ${isActive ? 'bg-white/15 text-white' : 'text-white/75 hover:text-white'}`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white text-xs text-slate-500">
        <div className="mx-auto flex max-w-7xl flex-wrap justify-between gap-2 px-4 py-4">
          <span>Titlivo · one parcel API across Maharashtra, Karnataka and Gujarat · all records synthetic</span>
          <span>
            Basemap © OpenStreetMap contributors, OpenFreeMap ·{' '}
            <a className="underline" href="https://github.com/Gurjas2112/Titlivo">GitHub</a>
          </span>
        </div>
      </footer>
    </div>
  )
}
