import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSurvey, getCameras, getAlerts } from '../api/client.js';
import CameraPanel from '../components/CameraPanel.jsx';
import UploadPanel from '../components/UploadPanel.jsx';
import TriageBoard from '../components/TriageBoard.jsx';
import AlertList from '../components/AlertList.jsx';
import { formatGPS } from '../lib/format.js';

const STATUS = {
  PENDING:    { label: 'Pending',    cls: 'bg-warn/10 text-warn' },
  PROCESSING: { label: 'Processing', cls: 'bg-amber/10 text-amber' },
  COMPLETE:   { label: 'Complete',   cls: 'bg-ok/10 text-ok' },
  FAILED:     { label: 'Failed',     cls: 'bg-danger/10 text-danger' },
};

function SectionLabel({ children }) {
  return (
    <div className="font-mono text-[9px] text-ink-mute uppercase tracking-[0.18em] mb-5">
      {children}
    </div>
  );
}

function Section({ label, children }) {
  return (
    <section>
      <SectionLabel>{label}</SectionLabel>
      {children}
    </section>
  );
}

export default function SurveyDetail() {
  const { id } = useParams();
  const [survey, setSurvey] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triageRefreshKey, setTriageRefreshKey] = useState(0);

  useEffect(() => {
    Promise.all([getSurvey(id), getCameras(id), getAlerts(id)])
      .then(([s, c, a]) => {
        setSurvey(s);
        setCameras(c);
        setAlerts(a);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const handleProcessingComplete = useCallback(() => {
    setTriageRefreshKey((k) => k + 1);
    getAlerts(id).then(setAlerts).catch(() => {});
  }, [id]);

  if (loading) {
    return (
      <div className="px-10 py-10">
        <div className="animate-pulse space-y-5 max-w-3xl">
          <div className="h-9 bg-surface rounded-lg w-80" />
          <div className="h-4 bg-surface rounded w-52" />
        </div>
      </div>
    );
  }

  if (!survey) {
    return (
      <div className="px-10 py-10 font-sans text-sm text-ink-mute">
        Survey not found.{' '}
        <Link to="/" className="text-amber hover:text-amber-hover transition-colors duration-150">
          Go back
        </Link>
      </div>
    );
  }

  const status = STATUS[survey.status] || STATUS.PENDING;
  const gps = formatGPS(survey.lat, survey.lng);

  return (
    <div className="px-10 py-10 max-w-6xl space-y-14">
      {/* Breadcrumb */}
      <div>
        <Link
          to="/"
          className="font-mono text-[10px] text-ink-mute hover:text-ink transition-colors duration-150 uppercase tracking-widest"
        >
          Surveys
        </Link>
        <span className="font-mono text-[10px] text-ink-mute/40 mx-2">/</span>
        <span className="font-mono text-[10px] text-ink-soft">{survey.name}</span>
      </div>

      {/* Survey header */}
      <Section label="Survey">
        <div className="flex items-start gap-5">
          <div className="flex-1 space-y-1.5">
            <h1 className="font-display text-4xl font-medium text-ink tracking-tight leading-tight">
              {survey.name}
            </h1>
            {survey.location_name && (
              <div className="font-sans text-sm text-ink-soft">{survey.location_name}</div>
            )}
            {gps && (
              <div className="font-mono text-[11px] text-ink-mute">{gps}</div>
            )}
          </div>
          <span
            className={`font-mono text-[9px] px-2.5 py-1 rounded-full uppercase tracking-[0.15em] shrink-0 mt-1 ${status.cls}`}
          >
            {status.label}
          </span>
        </div>
      </Section>

      {/* Cameras */}
      <Section label="Cameras">
        <CameraPanel
          surveyId={id}
          cameras={cameras}
          onCameraAdded={(cam) => setCameras((prev) => [...prev, cam])}
        />
      </Section>

      {/* Upload */}
      <Section label="Upload">
        {cameras.length === 0 ? (
          <p className="font-sans text-sm text-ink-mute">
            Add at least one camera before uploading images.
          </p>
        ) : (
          <UploadPanel
            surveyId={id}
            cameras={cameras}
            onComplete={handleProcessingComplete}
          />
        )}
      </Section>

      {/* Triage results */}
      <Section label="Triage results">
        <TriageBoard surveyId={id} refreshKey={triageRefreshKey} />
      </Section>

      {/* Alerts */}
      <Section label="Alerts">
        <AlertList alerts={alerts} />
      </Section>
    </div>
  );
}
