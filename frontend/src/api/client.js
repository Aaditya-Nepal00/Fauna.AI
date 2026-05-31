const API = 'http://localhost:8000';

export const getSurveys = () =>
  fetch(`${API}/api/surveys/`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const getSurvey = (id) =>
  fetch(`${API}/api/surveys/${id}`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const createSurvey = (data) =>
  fetch(`${API}/api/surveys/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const deleteSurvey = (id) =>
  fetch(`${API}/api/surveys/${id}`, { method: 'DELETE' });

export const getCameras = (surveyId) =>
  fetch(`${API}/api/cameras/${surveyId}`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const createCamera = (data) =>
  fetch(`${API}/api/cameras/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const getSummary = (surveyId) =>
  fetch(`${API}/api/surveys/${surveyId}/summary`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const getResults = (surveyId, { triage, flank } = {}) => {
  const params = new URLSearchParams();
  if (triage) params.set('triage', triage);
  if (flank) params.set('flank', flank);
  const qs = params.toString();
  return fetch(`${API}/api/surveys/${surveyId}/results${qs ? '?' + qs : ''}`)
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
};

export const getAlerts = (surveyId) =>
  fetch(`${API}/api/alerts/${surveyId}`).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const resolveAlert = (alertId) =>
  fetch(`${API}/api/alerts/${alertId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

export const imageUrl = (url) => `${API}${url}`;

export const uploadImages = (surveyId, cameraId, files, onEvent) => {
  const formData = new FormData();
  formData.append('camera_id', cameraId);
  for (const file of files) formData.append('files', file);

  fetch(`${API}/api/surveys/${surveyId}/upload`, {
    method: 'POST',
    body: formData,
  })
    .then(async (response) => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() ?? '';
        for (const block of blocks) {
          if (!block.trim()) continue;
          let eventType = 'message';
          let eventData = null;
          for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) {
              try { eventData = JSON.parse(line.slice(6)); } catch { /* skip */ }
            }
          }
          if (eventData !== null) onEvent({ ...eventData, _event: eventType });
        }
      }
    })
    .catch(console.error);
};
