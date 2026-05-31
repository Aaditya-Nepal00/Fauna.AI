import { useState, useRef, useCallback } from 'react';

export default function UploadZone({ cameras, onStartProcessing }) {
  const [files, setFiles] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(cameras[0]?.id ?? '');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const acceptFiles = useCallback((fileList) => {
    const images = Array.from(fileList).filter(f => f.type.startsWith('image/'));
    if (images.length) setFiles(images);
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    acceptFiles(e.dataTransfer.files);
  };

  const canStart = files.length > 0 && selectedCamera;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? '#40916C' : '#1B4332'}`,
          borderRadius: '12px',
          padding: '48px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragging ? 'rgba(64,145,108,0.06)' : 'transparent',
          transition: 'border-color 0.15s, background 0.15s',
        }}
        onMouseEnter={e => { if (!dragging) e.currentTarget.style.borderColor = '#2D6A4F'; }}
        onMouseLeave={e => { if (!dragging) e.currentTarget.style.borderColor = '#1B4332'; }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*"
          style={{ display: 'none' }}
          onChange={e => acceptFiles(e.target.files)}
        />

        <div style={{ fontSize: '28px', color: '#374151', marginBottom: '10px' }}>⬆</div>

        {files.length === 0 ? (
          <>
            <p style={{ fontSize: '14px', fontWeight: 500, color: '#d1d5db' }}>
              Drop camera trap images or click to select
            </p>
            <p style={{ fontSize: '12px', color: '#4b5563', marginTop: '4px' }}>
              JPG, PNG, TIFF — select multiple files at once
            </p>
          </>
        ) : (
          <>
            <p style={{ fontSize: '14px', fontWeight: 500, color: '#52B788', fontFamily: 'monospace' }}>
              {files.length} image{files.length !== 1 ? 's' : ''} selected
            </p>
            <p style={{ fontSize: '12px', color: '#4b5563', marginTop: '4px' }}>
              {files[0].name}{files.length > 1 ? ` + ${files.length - 1} more` : ''}
            </p>
          </>
        )}
      </div>

      {/* Controls row */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>
            Assign to camera
          </label>
          <select
            value={selectedCamera}
            onChange={e => setSelectedCamera(e.target.value)}
            style={{
              width: '100%',
              background: '#0F1A14',
              border: '1px solid #1B4332',
              borderRadius: '8px',
              padding: '8px 10px',
              fontSize: '13px',
              color: '#e5e7eb',
              outline: 'none',
              fontFamily: 'inherit',
              cursor: 'pointer',
            }}
          >
            {cameras.map(cam => (
              <option key={cam.id} value={cam.id}>{cam.label}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => canStart && onStartProcessing(selectedCamera, files)}
          disabled={!canStart}
          style={{
            padding: '8px 24px',
            background: canStart ? '#2D6A4F' : '#1B4332',
            color: canStart ? '#fff' : '#374151',
            border: 'none',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            cursor: canStart ? 'pointer' : 'not-allowed',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={e => { if (canStart) e.currentTarget.style.background = '#40916C'; }}
          onMouseLeave={e => { if (canStart) e.currentTarget.style.background = '#2D6A4F'; }}
        >
          Start Processing
        </button>
      </div>
    </div>
  );
}
