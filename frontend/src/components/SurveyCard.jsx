import { useNavigate } from 'react-router-dom';
import { formatGPS, formatDate } from '../lib/format.js';

const STATUS = {
  PENDING:    { label: 'Pending',    cls: 'bg-warn/10 text-warn' },
  PROCESSING: { label: 'Processing', cls: 'bg-amber/10 text-amber' },
  COMPLETE:   { label: 'Complete',   cls: 'bg-ok/10 text-ok' },
  FAILED:     { label: 'Failed',     cls: 'bg-danger/10 text-danger' },
};

export default function SurveyCard({ survey }) {
  const navigate = useNavigate();
  const status = STATUS[survey.status] || STATUS.PENDING;
  const gps = formatGPS(survey.lat, survey.lng);

  return (
    <div
      onClick={() => navigate(`/survey/${survey.id}`)}
      className="bg-surface border border-line/30 rounded-xl p-6 cursor-pointer hover:bg-raised hover:border-line/60 transition-all duration-150 group flex flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-display text-[17px] font-medium text-ink leading-snug">
          {survey.name}
        </h2>
        <span className={`font-mono text-[9px] px-2 py-0.5 rounded-full shrink-0 uppercase tracking-widest ${status.cls}`}>
          {status.label}
        </span>
      </div>

      <div className="space-y-1">
        {survey.location_name && (
          <div className="font-sans text-xs text-ink-soft">{survey.location_name}</div>
        )}
        {gps && (
          <div className="font-mono text-[11px] text-ink-mute">{gps}</div>
        )}
        {survey.camera_count > 0 && (
          <div className="font-mono text-[11px] text-ink-mute">
            {survey.camera_count} {survey.camera_count === 1 ? 'camera' : 'cameras'}
          </div>
        )}
      </div>

      <div className="mt-auto flex items-center justify-between pt-3 border-t border-line/20">
        <span className="font-mono text-[10px] text-ink-mute">{formatDate(survey.created_at)}</span>
        <span className="font-mono text-[10px] text-amber group-hover:text-amber-hover transition-colors duration-150 uppercase tracking-widest">
          Open
        </span>
      </div>
    </div>
  );
}
