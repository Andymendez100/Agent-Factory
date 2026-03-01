import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import PlatformsPage from "./pages/PlatformsPage";
import TasksPage from "./pages/TasksPage";
import RunsPage from "./pages/RunsPage";
import RunMonitorPage from "./pages/RunMonitorPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/platforms" replace />} />
          <Route path="/platforms" element={<PlatformsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/runs/:runId" element={<RunMonitorPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
