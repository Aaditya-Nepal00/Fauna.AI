const BAND_STYLES = {
  CONFIRMED: { dot: '#22c55e', label: 'CONFIRMED', color: '#4ade80', bg: 'rgba(34,197,94,0.1)' },
  REVIEW:    { dot: '#eab308', label: 'REVIEW',    color: '#fbbf24', bg: 'rgba(234,179,8,0.12)' },
  EMPTY:     { dot: '#4b5563', label: 'EMPTY',     color: '#6b7280', bg: 'rgba(75,85,99,0.15)' },
  BLUR:      { dot: '#ef4444', label: 'BLUR',      color: '#f87171', bg: 'rgba(239,68,68,0.1)' },
};

function formatDatetime(iso) {
  if (!iso) return 'No EXIF data';
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    });
  } catch {
    return 'No EXIF data';
  }
}

// Deterministic flank assignment based on image ID
function getFlank(imageId) {
  if (!imageId) return 'Left Flank';
  const last = imageId.slice(-1);
  return parseInt(last, 16) % 2 === 0 ? 'Left Flank' : 'Right Flank';
}

export default function ImageCard({ result, showFlank = false }) {
  const { id, filename, band, species, confidence, captured_at, camera_label } = result;
  const style = BAND_STYLES[band] ?? BAND_STYLES.EMPTY;
  const isTiger = species?.toLowerCase().includes('tiger');

  return (
    <div style={{
      background: '#0F1A14',
      border: '1px solid #1B4332',
      borderRadius: '10px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#2D6A4F'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#1B4332'}
    >
      {/* Thumbnail placeholder */}
      <div style={{
        aspectRatio: '16/9',
        background: '#1A2E1F',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Band dot indicator */}
        <div style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: style.dot,
          boxShadow: `0 0 6px ${style.dot}`,
        }} />
        <span style={{ fontFamily: 'monospace', fontSize: '10px', color: '#374151', padding: '0 8px', textAlign: 'center', wordBreak: 'break-all' }}>
          {filename}
        </span>
      </div>

      {/* Info */}
      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '7px', flex: 1 }}>
        {/* Species + confidence */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '6px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500, color: isTiger ? '#FCBF49' : '#e5e7eb', lineHeight: 1.3 }}>
            {species ?? 'No subject'}
          </span>
          {confidence != null && (
            <span style={{
              flexShrink: 0,
              fontSize: '11px',
              fontFamily: 'monospace',
              padding: '1px 6px',
              borderRadius: '4px',
              background: style.bg,
              color: style.color,
            }}>
              {confidence.toFixed(2)}
            </span>
          )}
        </div>

        {/* Badges row */}
        <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '10px',
            fontFamily: 'monospace',
            padding: '2px 7px',
            borderRadius: '4px',
            background: style.bg,
            color: style.color,
            fontWeight: 600,
          }}>
            {style.label}
          </span>
          {showFlank && isTiger && (
            <span style={{
              fontSize: '10px',
              padding: '2px 7px',
              borderRadius: '4px',
              background: 'rgba(247,127,0,0.15)',
              color: '#F77F00',
              fontWeight: 500,
            }}>
              {getFlank(id)}
            </span>
          )}
        </div>

        {/* Metadata */}
        <div style={{ borderTop: '1px solid #1A2E1F', paddingTop: '7px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
          <p style={{ fontSize: '11px', color: '#4b5563' }}>{formatDatetime(captured_at)}</p>
          {camera_label && (
            <p style={{ fontSize: '11px', color: '#374151' }}>{camera_label}</p>
          )}
        </div>
      </div>
    </div>
  );
}
