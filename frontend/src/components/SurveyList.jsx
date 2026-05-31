import { useNavigate } from 'react-router-dom';

const STATUS_STYLES = {
  PENDING:    { bg: '#1f2937', color: '#9ca3af' },
  PROCESSING: { bg: '#451a03', color: '#FCBF49' },
  COMPLETE:   { bg: '#052e16', color: '#52B788' },
};

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function SurveyCard({ survey, onDelete }) {
  const navigate = useNavigate();
  const status = survey.status ?? 'PENDING';
  const statusStyle = STATUS_STYLES[status] ?? STATUS_STYLES.PENDING;

  return (
    <div
      onClick={() => navigate(`/survey/${survey.id}`)}
      style={{
        background: '#0F1A14',
        border: '1px solid #1B4332',
        borderRadius: '10px',
        padding: '16px',
        cursor: 'pointer',
        transition: 'border-color 0.15s',
        position: 'relative',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#2D6A4F'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#1B4332'}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div style={{ minWidth: 0 }}>
          <h3 style={{ fontWeight: 500, color: '#f3f4f6', fontSize: '14px', marginBottom: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {survey.name}
          </h3>
          <p style={{ fontSize: '12px', color: '#6b7280' }}>{survey.location_name}</p>
        </div>
        <span style={{
          flexShrink: 0,
          fontSize: '10px',
          padding: '2px 8px',
          borderRadius: '4px',
          fontWeight: 600,
          fontFamily: 'monospace',
          background: statusStyle.bg,
          color: statusStyle.color,
        }}>
          {status}
        </span>
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', gap: '12px', marginTop: '12px', fontSize: '12px', color: '#4b5563' }}>
        <span>{survey.camera_count ?? 0} cameras</span>
        <span style={{ color: '#1f2937' }}>·</span>
        <span>{formatDate(survey.created_at)}</span>
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #1A2E1F' }}>
        <span style={{ fontSize: '11px', color: '#40916C' }}>Open survey →</span>
        <button
          onClick={e => { e.stopPropagation(); onDelete(survey.id); }}
          style={{ fontSize: '11px', color: '#374151', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          onMouseEnter={e => e.currentTarget.style.color = '#f87171'}
          onMouseLeave={e => e.currentTarget.style.color = '#374151'}
        >
          Delete
        </button>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div style={{ background: '#0F1A14', border: '1px solid #1B4332', borderRadius: '10px', padding: '16px' }}>
      <div style={{ height: '14px', background: '#1A2E1F', borderRadius: '4px', width: '70%', marginBottom: '8px' }} />
      <div style={{ height: '12px', background: '#1A2E1F', borderRadius: '4px', width: '45%' }} />
      <div style={{ height: '12px', background: '#1A2E1F', borderRadius: '4px', width: '35%', marginTop: '12px' }} />
    </div>
  );
}

export default function SurveyList({ surveys, loading, onDelete }) {
  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '12px',
  };

  if (loading) {
    return (
      <div style={gridStyle}>
        {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (surveys.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '64px 0', color: '#4b5563' }}>
        <div style={{ fontSize: '32px', marginBottom: '12px' }}>◈</div>
        <p style={{ fontSize: '13px' }}>No surveys yet. Create one to get started.</p>
      </div>
    );
  }

  return (
    <div style={gridStyle}>
      {surveys.map(s => (
        <SurveyCard key={s.id} survey={s} onDelete={onDelete} />
      ))}
    </div>
  );
}
