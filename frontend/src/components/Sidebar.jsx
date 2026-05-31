import { NavLink } from 'react-router-dom';

export default function Sidebar() {
  return (
    <aside
      className="fixed left-0 top-0 bottom-0 flex flex-col border-r border-line/30 z-20"
      style={{
        width: '240px',
        background: '#15110D',
        backgroundImage:
          'repeating-linear-gradient(135deg, transparent, transparent 12px, rgba(255,255,255,0.018) 12px, rgba(255,255,255,0.018) 13px)',
      }}
    >
      {/* Brand */}
      <div className="px-6 pt-8 pb-6">
        <div className="font-display text-[22px] font-semibold text-ink tracking-tight">
          Fauna.AI
        </div>
        <div className="font-mono text-[9px] text-ink-mute tracking-[0.18em] mt-1 uppercase">
          Camera Trap Intelligence
        </div>
      </div>

      <div className="h-px bg-line/30 mx-5" />

      {/* Nav */}
      <nav className="flex-1 px-3 pt-4 space-y-0.5">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors duration-150 ${
              isActive
                ? 'text-ink bg-raised border-l-2 border-amber pl-[10px]'
                : 'text-ink-soft hover:text-ink hover:bg-raised/50'
            }`
          }
        >
          Surveys
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="px-6 pb-7">
        <div className="font-mono text-[9px] text-ink-mute leading-relaxed tracking-wide">
          eSewa × WWF Nepal
        </div>
        <div className="font-mono text-[9px] text-ink-mute/50 mt-1">v1.0.0</div>
      </div>
    </aside>
  );
}
