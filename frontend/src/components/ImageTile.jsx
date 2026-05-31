import { useState } from 'react';
import { imageUrl } from '../api/client.js';
import { formatDateTime, formatConfidence } from '../lib/format.js';

function FlankBadge({ flank }) {
  if (!flank) return null;
  const isLeft = flank === 'LEFT';
  return (
    <span
      className={`font-mono text-[9px] px-1.5 py-0.5 rounded uppercase tracking-widest shrink-0 ml-2 ${
        isLeft ? 'text-amber bg-amber/12' : 'text-teal bg-teal/12'
      }`}
    >
      {flank}
    </span>
  );
}

function SpeciesLabel({ image }) {
  if (image.species) return image.species;
  if (image.triage) {
    return image.triage
      .replace('_', ' ')
      .toLowerCase()
      .replace(/^\w/, (c) => c.toUpperCase());
  }
  return '—';
}

export default function ImageTile({ image, onClick }) {
  const [loaded, setLoaded] = useState(false);
  const [errored, setErrored] = useState(false);

  return (
    <div
      onClick={() => onClick?.(image)}
      className="bg-surface border border-line/30 rounded-xl overflow-hidden cursor-pointer hover:border-line/60 hover:bg-raised group transition-all duration-150"
    >
      {/* Image */}
      <div className="relative bg-raised" style={{ aspectRatio: '4/3' }}>
        {!errored && image.image_url ? (
          <>
            {!loaded && (
              <div className="absolute inset-0 animate-pulse bg-raised" />
            )}
            <img
              src={imageUrl(image.image_url)}
              alt={image.filename}
              loading="lazy"
              onLoad={() => setLoaded(true)}
              onError={() => setErrored(true)}
              className={`w-full h-full object-cover transition-opacity duration-200 ${
                loaded ? 'opacity-100' : 'opacity-0'
              }`}
            />
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono text-[10px] text-ink-mute">No image</span>
          </div>
        )}

        {/* Confidence badge */}
        {image.species_confidence != null && (
          <div className="absolute top-2 right-2 font-mono text-[10px] bg-base/75 text-ink-soft px-1.5 py-0.5 rounded-md backdrop-blur-sm">
            {formatConfidence(image.species_confidence)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="px-3 py-3">
        <div className="flex items-center justify-between mb-1">
          <span className="font-sans text-[13px] text-ink font-medium truncate">
            <SpeciesLabel image={image} />
          </span>
          <FlankBadge flank={image.flank} />
        </div>
        <div className="font-mono text-[10px] text-ink-mute leading-relaxed">
          {formatDateTime(image.captured_at)}
        </div>
        {image.camera_label && (
          <div className="font-mono text-[10px] text-ink-mute">{image.camera_label}</div>
        )}
      </div>
    </div>
  );
}
