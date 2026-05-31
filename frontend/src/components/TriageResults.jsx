import { useState, useEffect } from 'react';
import { api } from '../api/client.js';
import ImageCard from './ImageCard.jsx';

const TABS = [
  {
    key: 'tiger',
    label: 'Tiger',
    filterFn: r => (r.band === 'CONFIRMED' || r.band === 'REVIEW') && r.species?.toLowerCase().includes('tiger'),
    accentColor: '#FCBF49',
    accentBg: 'rgba(252,191,73,0.12)',
  },
  {
    key: 'wildlife',
    label: 'Other Wildlife',
    filterFn: r => (r.band === 'CONFIRMED' || r.band === 'REVIEW') && r.species && !r.species.toLowerCase().includes('tiger') && !r.species.toLowerCase().includes('human'),
    accentColor: '#52B788',
    accentBg: 'rgba(82,183,136,0.12)',
  },
  {
    key: 'human',
    label: 'Human',
    filterFn: r => (r.band === 'CONFIRMED' || r.band === 'REVIEW') && r.species?.toLowerCase().includes('human'),
    accentColor: '#60a5fa',
    accentBg: 'rgba(96,165,250,0.12)',
  },
  {
    key: 'empty',
    label: 'Non-object',
    filterFn: r => r.band === 'EMPTY',
    accentColor: '#4b5563',
    accentBg: 'rgba(75,85,99,0.12)',
  },
  {
    key: 'blur',
    label: 'Blur',
    filterFn: r => r.band === 'BLUR',
    accentColor: '#f87171',
    accentBg: 'rgba(248,113,113,0.12)',
  },
];

function SkeletonGrid() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px' }}>
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} style={{ background: '#0F1A14', borderRadius: '10px', aspectRatio: '16/9', animation: 'pulse 1.5s ease-in-out infinite', opacity: 0.5 }} />
      ))}
    </div>
  );
}

export default function TriageResults({ surveyId }) {
  const [results, setResults] = useState([]);
  const [activeTab, setActiveTab] = useState('tiger');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getResults(surveyId)
      .then(setResults)
      .catch(() => setError('Failed to load results from server.'))
      .finally(() => setLoading(false));
  }, [surveyId]);

  if (loading) return <SkeletonGrid />;
  if (error) return (
    <p style={{ color: '#f87171', fontSize: '13px' }}>{error}</p>
  );

  const tabsWithCounts = TABS.map(t => ({ ...t, count: results.filter(t.filterFn).length }));
  const active = TABS.find(t => t.key === activeTab);
  const filtered = active ? results.filter(active.filterFn) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '2px', borderBottom: '1px solid #1B4332', overflowX: 'auto' }}>
        {tabsWithCounts.map(tab => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '9px 14px',
                fontSize: '13px',
                background: 'none',
                border: 'none',
                borderBottom: isActive ? `2px solid ${tab.accentColor}` : '2px solid transparent',
                color: isActive ? '#e5e7eb' : '#4b5563',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                fontFamily: 'inherit',
                marginBottom: '-1px',
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.color = '#9ca3af'; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.color = '#4b5563'; }}
            >
              {tab.label}
              <span style={{
                fontSize: '11px',
                fontFamily: 'monospace',
                padding: '1px 6px',
                borderRadius: '4px',
                background: isActive ? tab.accentBg : 'rgba(31,41,55,0.6)',
                color: isActive ? tab.accentColor : '#374151',
              }}>
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Results grid */}
      {filtered.length === 0 ? (
        <p style={{ fontSize: '13px', color: '#374151', textAlign: 'center', padding: '32px 0' }}>
          No images in this category.
        </p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px' }}>
          {filtered.map(r => (
            <ImageCard key={r.id} result={r} showFlank={activeTab === 'tiger'} />
          ))}
        </div>
      )}
    </div>
  );
}
