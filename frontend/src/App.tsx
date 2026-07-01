
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { UploadView } from './views/UploadView';
import { ChartBuilderView } from './views/ChartBuilderView';
import { DashboardManagerView } from './views/DashboardManagerView';
import { DashboardBuilderView } from './views/DashboardBuilderView';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    }
  }
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<UploadView />} />
            <Route path="/dataset/:datasetId/charts" element={<ChartBuilderView />} />
            <Route path="/dataset/:datasetId/dashboards" element={<DashboardManagerView />} />
            <Route path="/dataset/:datasetId/dashboards/:dashboardId" element={<DashboardBuilderView />} />
          </Routes>
        </Layout>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
