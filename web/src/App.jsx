import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import AgentPage from './pages/AgentPage';
import WorkflowPage from './pages/WorkflowPage';
import WorkflowBuilder from './pages/WorkflowBuilder';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/agent" replace />} />
        <Route path="/agent" element={<AgentPage />} />
        <Route path="/workflow" element={<WorkflowPage />} />
        <Route path="/workflow-builder" element={<WorkflowBuilder />} />
      </Routes>
    </Layout>
  );
}

export default App;
