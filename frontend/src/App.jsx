import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './pages/Dashboard.jsx';
import SurveyDetail from './pages/SurveyDetail.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-base">
        <Sidebar />
        <main className="flex-1 min-h-screen" style={{ marginLeft: '240px' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/survey/:id" element={<SurveyDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
