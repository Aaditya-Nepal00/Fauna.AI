import { useRef, useState } from 'react';
import { uploadImages, getSummary } from '../api/client.js';
import ProcessingBar from './ProcessingBar.jsx';

export default function UploadPanel({ surveyId, cameras, onComplete }) {
  const [files, setFiles] = useState([]);
  const [cameraId, setCameraId] = useState('');
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(null);
  const inputRef = useRef(null);
  const seenIds = useRef(new Set());

  function handleFiles(fileList) {
    const imgs = Array.from(fileList).filter(
      (f) => f.type.startsWith('image/') || /\.(jpe?g|png|tiff?|bmp|raw|cr2|nef|arw)$/i.test(f.name)
    );
    setFiles(imgs);
  }

  function handleDrop(e) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  function handleStart() {
    if (!cameraId || files.length === 0) return;
    setProcessing(true);
    seenIds.current.clear();
    setProgress({
      current: 0,
      total: files.length,
      pct: 0,
      counts: { TIGER: 0, OTHER_WILDLIFE: 0, HUMAN: 0, NON_OBJECT: 0, BLUR: 0 },
      done: false,
    });

    uploadImages(surveyId, cameraId, files, async (event) => {
      if (event._event === 'image_processed') {
        // Guard: only count each image_id once
        if (seenIds.current.has(event.image_id)) return;
        seenIds.current.add(event.image_id);

        setProgress((prev) => {
          const counts = { ...prev.counts };
          if (event.triage in counts) counts[event.triage]++;
          return {
            ...prev,
            current: event.index,
            total: event.total,
            pct: event.percent,
            counts,
          };
        });
      } else if (event._event === 'analysis_complete') {
        // Fetch authoritative counts from the summary endpoint — single source of truth
        try {
          const summary = await getSummary(surveyId);
          setProgress((prev) => ({
            ...prev,
            pct: 100,
            counts: summary.triage,
            done: true,
          }));
        } catch {
          setProgress((prev) => ({ ...prev, pct: 100, done: true }));
        }

        setTimeout(() => {
          setProcessing(false);
          setFiles([]);
          onComplete?.();
        }, 2000);
      }
    });
  }

  if (processing) {
    return <ProcessingBar progress={progress} />;
  }

  const hasFiles = files.length > 0;

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className={`
          border rounded-xl px-8 py-12 flex flex-col items-center text-center cursor-pointer
          transition-all duration-150
          ${hasFiles
            ? 'border-amber/50 bg-amber/5'
            : 'border-dashed border-line/50 hover:border-amber/40 hover:bg-raised/40'
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {hasFiles ? (
          <div>
            <div className="font-mono text-base text-amber mb-1">
              {files.length} {files.length === 1 ? 'image' : 'images'} selected
            </div>
            <div className="font-mono text-[11px] text-ink-mute">
              {files[0].name}
              {files.length > 1 ? ` and ${files.length - 1} more` : ''}
            </div>
          </div>
        ) : (
          <div>
            <div className="font-sans text-sm text-ink-soft mb-1.5">
              Drop images here, or click to browse
            </div>
            <div className="font-mono text-[11px] text-ink-mute">
              JPEG · PNG · TIFF · RAW
            </div>
          </div>
        )}
      </div>

      {/* Camera select + start button */}
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="block font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em] mb-2">
            Assign to camera
          </label>
          <div className="relative">
            <select
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              className="w-full bg-base border border-line/40 rounded-lg px-3 py-2.5 text-sm text-ink font-sans appearance-none focus:outline-none focus:border-amber/60 transition-colors duration-150 pr-8"
            >
              <option value="">Select camera</option>
              {cameras.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  {cam.label}
                </option>
              ))}
            </select>
            {/* Chevron */}
            <svg
              className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-mute pointer-events-none"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        <button
          onClick={handleStart}
          disabled={!cameraId || !hasFiles}
          className="px-6 py-2.5 bg-amber hover:bg-amber-hover disabled:bg-amber-dim disabled:cursor-not-allowed rounded-lg text-sm font-medium text-base font-sans transition-colors duration-150 whitespace-nowrap"
        >
          Start processing
        </button>
      </div>
    </div>
  );
}
