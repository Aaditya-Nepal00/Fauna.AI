import { NavLink, Outlet } from 'react-router-dom';

function NavItem({ to, icon, children }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
          isActive
            ? 'bg-forest-700 text-forest-300'
            : 'text-gray-500 hover:text-gray-200 hover:bg-forest-800'
        }`
      }
    >
      <span className="w-4 h-4 flex-shrink-0">{icon}</span>
      {children}
    </NavLink>
  );
}

const IconGrid = () => (
  <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="1" y="1" width="5.5" height="5.5" rx="0.75" />
    <rect x="9.5" y="1" width="5.5" height="5.5" rx="0.75" />
    <rect x="1" y="9.5" width="5.5" height="5.5" rx="0.75" />
    <rect x="9.5" y="9.5" width="5.5" height="5.5" rx="0.75" />
  </svg>
);

export default function Layout() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#0F1A14' }}>
      {/* Sidebar */}
      <aside
        style={{ width: '220px', flexShrink: 0, borderRight: '1px solid #1B4332', display: 'flex', flexDirection: 'column', background: '#0F1A14' }}
      >
        {/* Logo */}
        <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid #1B4332' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#FCBF49', fontSize: '20px', lineHeight: 1 }}>◈</span>
            <span style={{ fontWeight: 600, color: '#f3f4f6', letterSpacing: '-0.02em', fontSize: '15px' }}>
              Fauna.AI
            </span>
          </div>
          <p style={{ fontSize: '11px', color: '#4b5563', marginTop: '2px', marginLeft: '28px' }}>
            Camera Trap Monitor
          </p>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <p style={{ fontSize: '10px', fontWeight: 600, color: '#374151', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '0 8px', marginBottom: '6px' }}>
            Navigation
          </p>
          <NavItem to="/" icon={<IconGrid />}>
            Surveys
          </NavItem>
        </nav>

        {/* Footer */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #1B4332' }}>
          <p style={{ fontSize: '11px', color: '#374151' }}>eSewa × WWF Nepal</p>
          <p style={{ fontSize: '10px', color: '#1f2937', fontFamily: 'monospace', marginTop: '2px' }}>v1.0.0</p>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, overflowY: 'auto', background: '#1A2E1F' }}>
        <Outlet />
      </main>
    </div>
  );
}
