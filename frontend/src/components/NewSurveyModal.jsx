import { useState } from 'react';
import { createSurvey } from '../api/client.js';

function Field({ label, children }) {
  return (
    <div>
      <label className="block font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em] mb-2">
        {label}
      </label>
      {children}
    </div>
  );
}

const inputCls =
  'w-full bg-base border border-line/40 rounded-lg px-3 py-2.5 text-sm text-ink placeholder:text-ink-mute focus:outline-none focus:border-amber/60 transition-colors duration-150';

export default function NewSurveyModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', location_name: '', lat: '', lng: '' });
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        location_name: form.location_name || form.name,
        lat: form.lat !== '' ? parseFloat(form.lat) : null,
        lng: form.lng !== '' ? parseFloat(form.lng) : null,
      };
      const survey = await createSurvey(payload);
      onCreated(survey);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-base/75 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-surface border border-line/40 rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <h2 className="font-display text-2xl font-medium text-ink mb-7">New survey</h2>

        <form onSubmit={handleSubmit} className="space-y-5">
          <Field label="Survey name">
            <input
              className={inputCls + ' font-sans'}
              placeholder="Chitwan Block A — Spring 2025"
              value={form.name}
              onChange={set('name')}
              required
            />
          </Field>

          <Field label="Location">
            <input
              className={inputCls + ' font-sans'}
              placeholder="Chitwan National Park"
              value={form.location_name}
              onChange={set('location_name')}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Latitude">
              <input
                className={inputCls + ' font-mono'}
                placeholder="27.5291"
                type="number"
                step="any"
                value={form.lat}
                onChange={set('lat')}
              />
            </Field>
            <Field label="Longitude">
              <input
                className={inputCls + ' font-mono'}
                placeholder="84.3542"
                type="number"
                step="any"
                value={form.lng}
                onChange={set('lng')}
              />
            </Field>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 border border-line/40 rounded-lg text-sm text-ink-soft hover:text-ink hover:border-line/70 transition-colors duration-150 font-sans"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.name.trim()}
              className="flex-1 py-2.5 bg-amber hover:bg-amber-hover disabled:bg-amber-dim disabled:cursor-not-allowed rounded-lg text-sm text-base font-medium font-sans transition-colors duration-150"
            >
              {saving ? 'Creating...' : 'Create survey'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
