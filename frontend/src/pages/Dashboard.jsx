import { useState, useEffect } from 'react';
import { getSurveys } from '../api/client.js';
import SurveyCard from '../components/SurveyCard.jsx';
import NewSurveyModal from '../components/NewSurveyModal.jsx';

export default function Dashboard() {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    getSurveys()
      .then(setSurveys)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="px-10 py-10 max-w-6xl">
      <div className="flex items-baseline justify-between mb-9">
        <h1 className="font-display text-4xl font-medium text-ink tracking-tight">Surveys</h1>
        <button
          onClick={() => setShowNew(true)}
          className="px-4 py-2 bg-amber hover:bg-amber-hover text-base text-sm font-medium rounded-lg font-sans transition-colors duration-150"
        >
          New survey
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-surface rounded-xl h-44 animate-pulse border border-line/20" />
          ))}
        </div>
      ) : surveys.length === 0 ? (
        <div className="flex items-center justify-center py-28">
          <div className="text-center space-y-2">
            <p className="font-display text-lg text-ink-soft">No surveys yet</p>
            <p className="font-mono text-xs text-ink-mute">
              Create your first survey to begin processing camera trap images.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {surveys.map((survey) => (
            <SurveyCard key={survey.id} survey={survey} />
          ))}
        </div>
      )}

      {showNew && (
        <NewSurveyModal
          onClose={() => setShowNew(false)}
          onCreated={(survey) => {
            setSurveys((prev) => [survey, ...prev]);
            setShowNew(false);
          }}
        />
      )}
    </div>
  );
}
