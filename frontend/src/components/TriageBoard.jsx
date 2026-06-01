import { useState, useEffect } from 'react';
import { getResults, getSummary } from '../api/client.js';
import ImageTile from './ImageTile.jsx';
import ImageDetailModal from './ImageDetailModal.jsx';

const CATEGORIES = [
  { key: 'TIGER',          label: 'Tiger' },
  { key: 'FLANKS',         label: 'Flanks', summaryKey: 'TIGER' },
  { key: 'OTHER_WILDLIFE', label: 'Other wildlife' },
  { key: 'HUMAN',          label: 'Human' },
  { key: 'NON_OBJECT',     label: 'Non-object' },
  { key: 'BLUR',           label: 'Blur' },
];

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-3 xl:grid-cols-4 gap-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="bg-raised rounded-xl overflow-hidden animate-pulse">
          <div className="bg-raised" style={{ aspectRatio: '4/3' }} />
          <div className="p-3 space-y-2">
            <div className="h-3 bg-line/30 rounded w-3/4" />
            <div className="h-2 bg-line/30 rounded w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex items-center justify-center py-20">
      <span className="font-sans text-sm text-ink-mute">No images in this category</span>
    </div>
  );
}

function ImageGrid({ images, onClickImage }) {
  if (images.length === 0) return <EmptyState />;
  return (
    <div className="grid grid-cols-3 xl:grid-cols-4 gap-4">
      {images.map((img) => (
        <ImageTile key={img.id} image={img} onClick={onClickImage} />
      ))}
    </div>
  );
}

function FlankSection({ label, accent, count, images, onClickImage }) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <div
          className="w-[3px] h-5 rounded-full shrink-0"
          style={{ background: accent }}
        />
        <h3 className="font-display text-[15px] font-medium text-ink">{label}</h3>
        <span
          className="font-mono text-xs"
          style={{ color: accent }}
        >
          {count}
        </span>
      </div>
      <ImageGrid images={images} onClickImage={onClickImage} />
    </div>
  );
}

export default function TriageBoard({ surveyId, refreshKey }) {
  const [activeCategory, setActiveCategory] = useState('TIGER');
  const [summary, setSummary] = useState(null);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);

  // Fetch summary (counts — single source of truth)
  useEffect(() => {
    getSummary(surveyId).then(setSummary).catch(() => {});
  }, [surveyId, refreshKey]);

  // Fetch images for the active category (FLANKS reuses TIGER query)
  useEffect(() => {
    setLoading(true);
    const apiTriage = activeCategory === 'FLANKS' ? 'TIGER' : activeCategory;
    getResults(surveyId, { triage: apiTriage })
      .then(setImages)
      .catch(() => setImages([]))
      .finally(() => setLoading(false));
  }, [surveyId, activeCategory, refreshKey]);

  const leftFlank    = images.filter((img) => img.flank === 'LEFT');
  const rightFlank   = images.filter((img) => img.flank === 'RIGHT');
  const uncertainFlank = images.filter((img) => img.flank === 'UNCERTAIN');
  const noFlank      = images.filter((img) => !img.flank && img.triage === 'TIGER');

  return (
    <div>
      {/* Category tab bar */}
      <div className="flex border-b border-line/30 mb-8">
        {CATEGORIES.map(({ key, label, summaryKey }) => {
          const count = summary?.triage?.[summaryKey ?? key] ?? null;
          const isActive = activeCategory === key;
          return (
            <button
              key={key}
              onClick={() => setActiveCategory(key)}
              className={`
                flex items-baseline gap-2 px-5 py-3 border-b-2 text-sm
                transition-colors duration-150 whitespace-nowrap
                ${isActive
                  ? 'border-amber text-ink'
                  : 'border-transparent text-ink-soft hover:text-ink hover:border-line/40'
                }
              `}
            >
              <span className="font-sans">{label}</span>
              {count !== null && (
                <span className={`font-mono text-xs ${isActive ? 'text-amber' : 'text-ink-mute'}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tiger: left / right flank split */}
      {activeCategory === 'TIGER' ? (
        loading ? (
          <SkeletonGrid />
        ) : (
          <div className="space-y-12">
            <FlankSection
              label="Left flank"
              accent="#E8853A"
              count={summary?.flank?.LEFT ?? leftFlank.length}
              images={leftFlank}
              onClickImage={setSelectedImage}
            />

            <div className="h-px bg-line/20" />

            <FlankSection
              label="Right flank"
              accent="#4A9D8E"
              count={summary?.flank?.RIGHT ?? rightFlank.length}
              images={rightFlank}
              onClickImage={setSelectedImage}
            />

            {(uncertainFlank.length > 0 || (summary?.flank?.UNCERTAIN ?? 0) > 0) && (
              <>
                <div className="h-px bg-line/20" />
                <FlankSection
                  label="Uncertain flank"
                  accent="#6B7280"
                  count={summary?.flank?.UNCERTAIN ?? uncertainFlank.length}
                  images={uncertainFlank}
                  onClickImage={setSelectedImage}
                />
              </>
            )}

            {noFlank.length > 0 && (
              <>
                <div className="h-px bg-line/20" />
                <FlankSection
                  label="Flank undetermined"
                  accent="#7A7062"
                  count={noFlank.length}
                  images={noFlank}
                  onClickImage={setSelectedImage}
                />
              </>
            )}
          </div>
        )
      ) : activeCategory === 'FLANKS' ? (
        loading ? (
          <SkeletonGrid />
        ) : (
          <div className="space-y-10">
            <p className="font-sans text-[13px] text-ink-mute">
              Flank library — stripe patterns for individual ID
            </p>
            {(() => {
              // Use crop_url when available, fall back to full image for older records
              const flanksImages = images.map((img) => ({
                ...img,
                image_url: img.crop_url || img.image_url,
              }));
              const left      = flanksImages.filter((img) => img.flank === 'LEFT');
              const right     = flanksImages.filter((img) => img.flank === 'RIGHT');
              const uncertain = flanksImages.filter((img) => img.flank === 'UNCERTAIN');
              return (
                <div className="space-y-12">
                  <FlankSection
                    label="Left flank"
                    accent="#E8853A"
                    count={summary?.flank?.LEFT ?? left.length}
                    images={left}
                    onClickImage={setSelectedImage}
                  />
                  <div className="h-px bg-line/20" />
                  <FlankSection
                    label="Right flank"
                    accent="#4A9D8E"
                    count={summary?.flank?.RIGHT ?? right.length}
                    images={right}
                    onClickImage={setSelectedImage}
                  />
                  {(uncertain.length > 0 || (summary?.flank?.UNCERTAIN ?? 0) > 0) && (
                    <>
                      <div className="h-px bg-line/20" />
                      <FlankSection
                        label="Uncertain"
                        accent="#6B7280"
                        count={summary?.flank?.UNCERTAIN ?? uncertain.length}
                        images={uncertain}
                        onClickImage={setSelectedImage}
                      />
                    </>
                  )}
                </div>
              );
            })()}
          </div>
        )
      ) : loading ? (
        <SkeletonGrid />
      ) : (
        <ImageGrid images={images} onClickImage={setSelectedImage} />
      )}

      {selectedImage && (
        <ImageDetailModal image={selectedImage} onClose={() => setSelectedImage(null)} />
      )}
    </div>
  );
}
