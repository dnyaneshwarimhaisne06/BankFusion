import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import EmailVerified from "./pages/EmailVerified";
import Dashboard from "./pages/Dashboard.tsx";
import UploadStatement from "./pages/UploadStatement";
import Statements from "./pages/Statements";
import StatementDetail from "./pages/StatementDetail";
import Transactions from "./pages/Transactions.tsx";
import Analytics from "./pages/Analytics.tsx";
import ExportData from "./pages/ExportData";
import Settings from "./pages/Settings";
import JsonViewer from "./pages/JsonViewer";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App = () => (
  <ErrorBoundary>
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <TokenRedirector />
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/auth/verified" element={<EmailVerified />} />
            <Route path="/auth/verify" element={<EmailVerified />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <UploadStatement />
                </ProtectedRoute>
              }
            />
            <Route
              path="/statements"
              element={
                <ProtectedRoute>
                  <Statements />
                </ProtectedRoute>
              }
            />
            <Route
              path="/statements/:id"
              element={
                <ProtectedRoute>
                  <StatementDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/transactions"
              element={
                <ProtectedRoute>
                  <Transactions />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Analytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/export"
              element={
                <ProtectedRoute>
                  <ExportData />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/json-viewer"
              element={
                <ProtectedRoute>
                  <JsonViewer />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
  </ErrorBoundary>
);

export default App;

function TokenRedirector() {
  // SPA-friendly bootstrap: fix deep-link refresh by rewriting from 404.html redirect
  // 1) If "?p=/route" is present, rewrite the path without reload
  // 2) If Supabase tokens are in hash and route is not /auth, rewrite to /auth preserving hash
  if (typeof window !== 'undefined') {
    const params = new URLSearchParams(window.location.search);
    const p = params.get('p');
    if (p && window.location.pathname === '/') {
      window.history.replaceState(null, '', p + (window.location.hash || ''));
    }
    const hash = window.location.hash || '';
    if ((hash.includes('access_token=') || hash.includes('error=')) && window.location.pathname !== '/auth') {
      window.history.replaceState(null, '', '/auth' + hash);
    }
  }
  return null;
}
