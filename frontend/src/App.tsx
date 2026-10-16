import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import { Toaster } from "sonner";
import MainLayout from "./components/layout/MainLayout";
import { applyThemeMode } from "./lib/theme";
import { useSettingsStore } from "./stores/settings-store";
import { useGlobalSSE } from "./hooks/useGlobalSSE";
import "./App.css";
import "./studio.css";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const TemplateGallery = lazy(() => import("./pages/TemplateGallery"));
const EditorPage = lazy(() => import("./pages/EditorPage"));
const WorkspaceDetail = lazy(() => import("./pages/WorkspaceDetail"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const InterviewPage = lazy(() => import("./pages/InterviewPage"));

function SSEProvider() {
  useGlobalSSE();
  return null;
}

function RouteFallback() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      加载中...
    </div>
  );
}

function App() {
  useEffect(() => {
    applyThemeMode();

    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handleSystemChange = () => {
      if (useSettingsStore.getState().themeMode === "system") {
        applyThemeMode();
      }
    };
    mql.addEventListener("change", handleSystemChange);

    const unsubscribe = useSettingsStore.subscribe((state, prevState) => {
      if (state.themeMode !== prevState.themeMode) {
        applyThemeMode();
      }
    });

    return () => {
      mql.removeEventListener("change", handleSystemChange);
      unsubscribe();
    };
  }, []);

  return (
    <BrowserRouter>
      <SSEProvider />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            color: "hsl(var(--card-foreground))",
          },
        }}
      />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/workspace" replace />} />
            <Route path="templates" element={<TemplateGallery />} />
            <Route path="workspace" element={<Dashboard />} />
            <Route path="workspace/:id" element={<WorkspaceDetail />} />
            <Route
              path="workspace/:id/resumes/:resumeId/:tab"
              element={<WorkspaceDetail />}
            />
            <Route
              path="workspace/:id/resumes/:resumeId"
              element={<Navigate to="overview" replace />}
            />
            <Route
              path="workspace/:id/resumes"
              element={<Navigate to="../" replace />}
            />
          </Route>
          <Route path="workspace/:id/template/edit" element={<EditorPage />} />
          <Route
            path="workspace/:id/resumes/:resumeId/edit"
            element={<EditorPage />}
          />
          <Route
            path="workspace/:workspaceId/resumes/:resumeId/interview/:collectionId/:roundId"
            element={<InterviewPage />}
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
