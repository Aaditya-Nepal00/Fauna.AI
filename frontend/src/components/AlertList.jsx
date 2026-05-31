import { useState } from 'react';
import { resolveAlert } from '../api/client.js';
import { formatDateTime } from '../lib/format.js';

const SEVERITY = {
  HIGH:   { cls: 'border-danger/25 bg-danger/5',   label: 'text-danger' },
  MEDIUM: { cls: 'border-warn/25 bg-warn/5',       label: 'text-warn' },
  LOW:    { cls: 'border-ok/25 bg-ok/5',           label: 'text-ok' },
};

export default function AlertList({ alerts: initial }) {
  const [alerts, setAlerts] = useState(initial);

  async function handleResolve(alertId) {
    try {
      await resolveAlert(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, resolved: true } : a))
      );
    } catch (err) {
      console.error(err);
    }
  }

  if (alerts.length === 0) {
    return (
      <p className="font-sans text-sm text-ink-mute">No anomaly alerts for this survey.</p>
    );
  }

  const active   = alerts.filter((a) => !a.resolved);
  const resolved = alerts.filter((a) => a.resolved);

  return (
    <div className="space-y-2">
      {active.map((alert) => {
        const sev = SEVERITY[alert.severity] || SEVERITY.LOW;
        return (
          <div
            key={alert.id}
            className={`border rounded-xl px-5 py-4 flex items-start gap-4 ${sev.cls}`}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2 mb-1">
                <span className={`font-mono text-[9px] uppercase tracking-[0.15em] ${sev.label}`}>
                  {alert.severity}
                </span>
                <span className="font-sans text-sm text-ink font-medium">{alert.species}</span>
                <span className="font-mono text-[10px] text-ink-mute">
                  {alert.alert_type?.replace(/_/g, ' ').toLowerCase()}
                </span>
              </div>
              {alert.recommended_action && (
                <p className="font-sans text-xs text-ink-soft mb-1.5 leading-relaxed">
                  {alert.recommended_action}
                </p>
              )}
              <div className="font-mono text-[10px] text-ink-mute">
                {formatDateTime(alert.detected_at)}
              </div>
            </div>
            <button
              onClick={() => handleResolve(alert.id)}
              className="font-mono text-[9px] uppercase tracking-[0.15em] text-ink-mute hover:text-ink transition-colors duration-150 shrink-0 mt-0.5"
            >
              Resolve
            </button>
          </div>
        );
      })}

      {resolved.length > 0 && (
        <div className="pt-4 border-t border-line/20">
          <div className="font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em] mb-3">
            {resolved.length} resolved
          </div>
          {resolved.map((alert) => (
            <div
              key={alert.id}
              className="flex gap-3 items-baseline py-2 border-b border-line/10 last:border-0 opacity-40"
            >
              <span className="font-mono text-[9px] text-ink-mute uppercase tracking-widest">
                {alert.severity}
              </span>
              <span className="font-sans text-xs text-ink-mute">{alert.species}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
