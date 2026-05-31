function LiveBadge({ icon, label, count, color }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      padding: '7px 12px',
      background: '#0F1A14',
      border: '1px solid #1B4332',
      borderRadius: '8px',
    }}>
      <span style={{ fontSize: '13px' }}>{icon}</span>
      <span style={{ fontSize: '11px', color: '#6b7280' }}>{label}:</span>
      <span style={{ fontFamily: 'monospace', fontSize: '13px', fontWeight: 600, color }}>{count}</span>
    </div>
  );
}

export default function ProcessingView({ stats }) {
  const { total, processed, percent, tiger, wildlife, human, empty, blur } = stats;
  const pct = Math.min(100, percent ?? 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Progress */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', color: '#d1d5db' }}>
            Processing{' '}
            <span style={{ fontFamily: 'monospace', color: '#52B788' }}>{processed}</span>
            {' / '}
            <span style={{ fontFamily: 'monospace' }}>{total}</span>
            {' '}images
          </span>
          <span style={{ fontFamily: 'monospace', fontSize: '12px', color: '#4b5563' }}>
            {pct.toFixed(1)}%
          </span>
        </div>

        {/* Bar track */}
        <div style={{ height: '6px', background: '#0F1A14', borderRadius: '99px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #2D6A4F, #52B788)',
              borderRadius: '99px',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>

      {/* Live badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        <LiveBadge icon="🐯" label="Tiger"         count={tiger}   color="#FCBF49" />
        <LiveBadge icon="🐾" label="Other wildlife" count={wildlife} color="#52B788" />
        <LiveBadge icon="👤" label="Human"          count={human}   color="#60a5fa" />
        <LiveBadge icon="⚫" label="Non-object"     count={empty}   color="#4b5563" />
        <LiveBadge icon="🔴" label="Blur"           count={blur}    color="#f87171" />
      </div>

      {total > 0 && processed < total && (
        <p style={{ fontSize: '11px', color: '#374151', fontStyle: 'italic' }}>
          Running FrameGuard → SpeciesID pipeline…
        </p>
      )}
    </div>
  );
}
