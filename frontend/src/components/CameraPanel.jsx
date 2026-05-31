import { useState } from 'react';
import { createCamera } from '../api/client.js';
import { formatGPS } from '../lib/format.js';

const inputCls =
  'w-full bg-base border border-line/40 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-amber/60 transition-colors duration-150';

function Field({ label, children }) {
  return (
    <div>
      <label className="block font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em] mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}

export default function CameraPanel({ surveyId, cameras, onCameraAdded }) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ label: '', gps_lat: '', gps_lng: '', habitat_type: '' });
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleAdd(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const camera = await createCamera({
        survey_id: surveyId,
        label: form.label,
        gps_lat: form.gps_lat !== '' ? parseFloat(form.gps_lat) : null,
        gps_lng: form.gps_lng !== '' ? parseFloat(form.gps_lng) : null,
        habitat_type: form.habitat_type || null,
      });
      onCameraAdded(camera);
      setForm({ label: '', gps_lat: '', gps_lng: '', habitat_type: '' });
      setAdding(false);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      {cameras.length === 0 && !adding && (
        <p className="font-sans text-sm text-ink-mute mb-3">No cameras registered.</p>
      )}

      {cameras.length > 0 && (
        <div className="mb-5 space-y-0">
          {cameras.map((cam) => {
            const gps = formatGPS(cam.gps_lat, cam.gps_lng);
            return (
              <div
                key={cam.id}
                className="flex items-baseline gap-4 py-3 border-b border-line/20 last:border-0"
              >
                <span className="font-mono text-sm text-ink w-28 shrink-0">{cam.label}</span>
                {cam.habitat_type && (
                  <span className="font-mono text-xs text-ink-soft">{cam.habitat_type}</span>
                )}
                {gps && (
                  <span className="font-mono text-[11px] text-ink-mute ml-auto shrink-0">{gps}</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {adding ? (
        <form
          onSubmit={handleAdd}
          className="bg-raised border border-line/30 rounded-xl p-5 space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field label="Camera label">
                <input
                  className={inputCls + ' font-mono text-ink'}
                  placeholder="CAM-01"
                  value={form.label}
                  onChange={set('label')}
                  required
                />
              </Field>
            </div>
            <Field label="Latitude">
              <input
                className={inputCls + ' font-mono text-ink'}
                placeholder="27.5291"
                type="number"
                step="any"
                value={form.gps_lat}
                onChange={set('gps_lat')}
              />
            </Field>
            <Field label="Longitude">
              <input
                className={inputCls + ' font-mono text-ink'}
                placeholder="84.3542"
                type="number"
                step="any"
                value={form.gps_lng}
                onChange={set('gps_lng')}
              />
            </Field>
            <div className="col-span-2">
              <Field label="Habitat type">
                <input
                  className={inputCls + ' font-sans text-ink'}
                  placeholder="Dense forest, riverbank..."
                  value={form.habitat_type}
                  onChange={set('habitat_type')}
                />
              </Field>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setAdding(false)}
              className="px-4 py-2 text-xs text-ink-soft hover:text-ink border border-line/30 rounded-lg transition-colors duration-150 font-sans"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.label.trim()}
              className="px-4 py-2 text-xs bg-amber hover:bg-amber-hover disabled:bg-amber-dim rounded-lg text-base font-medium transition-colors duration-150 font-sans"
            >
              {saving ? 'Adding...' : 'Add camera'}
            </button>
          </div>
        </form>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="font-mono text-[11px] text-amber hover:text-amber-hover transition-colors duration-150 uppercase tracking-widest"
        >
          + Add camera
        </button>
      )}
    </div>
  );
}
