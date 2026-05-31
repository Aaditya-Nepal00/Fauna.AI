const CATEGORIES = [
  { key: 'TIGER',          label: 'Tiger' },
  { key: 'OTHER_WILDLIFE', label: 'Other wildlife' },
  { key: 'HUMAN',          label: 'Human' },
  { key: 'NON_OBJECT',     label: 'Non-object' },
  { key: 'BLUR',           label: 'Blur' },
];

export default function ProcessingBar({ progress }) {
  if (!progress) return null;
  const { current = 0, total = 0, pct = 0, counts = {}, done = false } = progress;

  return (
    <div className="space-y-5">
      {/* Bar + label */}
      <div>
        <div className="flex justify-between items-baseline mb-2.5">
          <span className="font-mono text-[9px] text-ink-mute uppercase tracking-[0.15em]">
            {done ? 'Complete' : 'Processing'}
          </span>
          <span className="font-mono text-sm text-ink">
            {current} / {total}&nbsp;&nbsp;·&nbsp;&nbsp;{Number(pct).toFixed(0)}%
          </span>
        </div>
        <div className="h-1 bg-raised rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${done ? 'bg-ok' : 'bg-amber'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Live category counters */}
      <div className="flex gap-8 flex-wrap">
        {CATEGORIES.map(({ key, label }) => (
          <div key={key}>
            <div className="font-mono text-2xl text-ink leading-none">{counts[key] ?? 0}</div>
            <div className="font-mono text-[9px] text-ink-mute uppercase tracking-[0.13em] mt-1">
              {label}
            </div>
          </div>
        ))}
      </div>

      {done && (
        <div className="font-mono text-[11px] text-ok tracking-wide">
          Analysis complete — results are ready below.
        </div>
      )}
    </div>
  );
}
