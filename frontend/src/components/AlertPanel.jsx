import { useState } from 'react';
import { api } from '../api/client.js';

const SEVERITY = {
  HIGH:   { borderColor: '#DC2626', bg: 'rgba(220,38,38,0.07)',  badgeBg: 'rgba(220,38,38,0.2)',  badgeColor: '#f87171' },
  MEDIUM: { borderColor: '#F77F00', bg: 'rgba(247,127,0,0.07)', badgeBg: 'rgba(247,127,0,0.2)',  badgeColor: '#FCBF49' },
  LOW:    { borderColor: '#65A30D', bg: 'rgba(101,163,13,0.07)', badgeBg: 'rgba(101,163,13,0.2)', badgeColor: '#a3e635' },
};

function daysAgo(iso) {
  if (!iso) return null;
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
}

function AlertCard({ alert, onResolved }) {
  const [resolving, setResolving] = useState(false);
  const s = SEVERITY[alert.severity] ?? SEVERITY.LOW;
  const lastSeen = daysAgo(alert.last_confirmed_sighting);

  const handleResolve = async () => {
    setResolving(true);
    try {
      await api.resolveAlert(alert.id);
      onResolved(alert.id);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0',
      borderRadius: '8px',
      overflow: 'hidden',
      border: '1px solid #1B4332',
      opacity: alert.resolved ? 0.5 : 1,
    }}>
      {/* Severity bar */}
      <div style={{ width: '4px', flexShrink: 0, background: s.borderColor, alignSelf: 'stretch' }} />

      {/* Content */}
      <div style={{ flex: 1, padding: '12px 14px', background: s.bg, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ minWidth: 0 }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#e5e7eb' }}>{alert.species}</span>
            <span style={{
              fontSize: '10px',
              fontFamily: 'monospace',
              fontWeight: 700,
              padding: '1px 7px',
              borderRadius: '4px',
              background: s.badgeBg,
              color: s.badgeColor,
            }}>
              {alert.severity}
            </span>
            <span style={{ fontSize: '11px', color: '#374151', fontFamily: 'monospace' }}>
              {alert.alert_type}
            </span>
          </div>

          {lastSeen && (
            <p style={{ fontSize: '11px', color: '#4b5563', marginBottom: '5px' }}>
              Last seen: {lastSeen}
            </p>
          )}

          <p style={{ fontSize: '12px', color: '#9ca3af', lineHeight: 1.5 }}>
            {alert.recommended_action}
          </p>
        </div>

        {!alert.resolved ? (
          <button
            onClick={handleResolve}
            disabled={resolving}
            style={{
              flexShrink: 0,
              padding: '5px 12px',
              fontSize: '11px',
              color: '#6b7280',
              background: 'none',
              border: '1px solid #1B4332',
              borderRadius: '6px',
              cursor: resolving ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              opacity: resolving ? 0.5 : 1,
            }}
            onMouseEnter={e => { if (!resolving) { e.currentTarget.style.color = '#e5e7eb'; e.currentTarget.style.borderColor = '#2D6A4F'; } }}
            onMouseLeave={e => { e.currentTarget.style.color = '#6b7280'; e.currentTarget.style.borderColor = '#1B4332'; }}
          >
            {resolving ? '…' : 'Resolve'}
          </button>
        ) : (
          <span style={{ fontSize: '11px', color: '#374151', flexShrink: 0 }}>Resolved</span>
        )}
      </div>
    </div>
  );
}

export default function AlertPanel({ alerts: initialAlerts }) {
  const [alerts, setAlerts] = useState(initialAlerts);

  const handleResolved = (id) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, resolved: true } : a));
  };

  if (alerts.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0', color: '#374151', fontSize: '13px' }}>
        No anomaly alerts detected for this survey.
      </div>
    );
  }

  const unresolved = alerts.filter(a => !a.resolved);
  const resolved = alerts.filter(a => a.resolved);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {unresolved.map(a => <AlertCard key={a.id} alert={a} onResolved={handleResolved} />)}

      {resolved.length > 0 && (
        <>
          <p style={{ fontSize: '11px', color: '#374151', paddingTop: '8px' }}>
            Resolved ({resolved.length})
          </p>
          {resolved.map(a => <AlertCard key={a.id} alert={a} onResolved={handleResolved} />)}
        </>
      )}
    </div>
  );
}
