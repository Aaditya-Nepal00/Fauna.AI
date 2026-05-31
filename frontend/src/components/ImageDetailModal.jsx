import { useEffect } from 'react';
import { imageUrl } from '../api/client.js';
import { formatDateTime, formatConfidence, formatGPS } from '../lib/format.js';

function MetaRow({ label, value, valueClass = '' }) {
  return (
    <div>
      <div className="font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em] mb-0.5">
        {label}
      </div>
      <div className={`font-mono text-[13px] break-all leading-snug ${valueClass || 'text-ink'}`}>
        {value ?? '—'}
      </div>
    </div>
  );
}

export default function ImageDetailModal({ image, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!image) return null;

  const flankValueClass =
    image.flank === 'LEFT' ? 'text-amber' : image.flank === 'RIGHT' ? 'text-teal' : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-base/85 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className="relative flex bg-surface border border-line/40 rounded-2xl overflow-hidden shadow-2xl"
        style={{ maxWidth: '900px', width: '100%', maxHeight: '90vh' }}
      >
        {/* Image pane */}
        <div className="flex-1 min-w-0 bg-base flex items-center justify-center overflow-hidden">
          {image.image_url ? (
            <img
              src={imageUrl(image.image_url)}
              alt={image.filename}
              className="max-w-full max-h-full object-contain"
              style={{ maxHeight: '90vh' }}
            />
          ) : (
            <div className="font-mono text-sm text-ink-mute p-16 text-center">
              No image on disk
            </div>
          )}
        </div>

        {/* Metadata panel */}
        <div
          className="shrink-0 border-l border-line/30 flex flex-col overflow-y-auto"
          style={{ width: '240px' }}
        >
          <div className="px-6 pt-6 pb-4 border-b border-line/20">
            <button
              onClick={onClose}
              className="font-mono text-[9px] text-ink-mute hover:text-ink uppercase tracking-[0.15em] transition-colors duration-150"
            >
              Close
            </button>
          </div>

          <div className="px-6 py-5 space-y-5">
            <MetaRow label="Filename" value={image.filename} />
            <MetaRow label="Species" value={image.species} />
            <MetaRow label="Confidence" value={formatConfidence(image.species_confidence)} />
            <MetaRow label="Triage" value={image.triage?.replace('_', ' ')} />
            <MetaRow
              label="Flank"
              value={image.flank}
              valueClass={flankValueClass}
            />
            <MetaRow label="Flank conf." value={formatConfidence(image.flank_confidence)} />
            <MetaRow label="FG confidence" value={formatConfidence(image.fg_confidence)} />
            <MetaRow label="Captured" value={formatDateTime(image.captured_at)} />
            <MetaRow label="Camera" value={image.camera_label} />
            <MetaRow label="Day / Night" value={image.is_night ? 'Night' : 'Day'} />
            <MetaRow label="Blur score" value={formatConfidence(image.blur_score)} />
            <MetaRow
              label="Dimensions"
              value={
                image.width && image.height
                  ? `${image.width} × ${image.height}`
                  : null
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}
