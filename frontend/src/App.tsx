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
  const navigate = useNavigate();
  // Lightweight global handler: if Supabase tokens are present on non-/auth routes, send to /auth
  // This ensures static hosting without rewrites still processes verification tokens reliably.
  if (typeof window !== 'undefined') {
    const hash = window.location.hash || '';
    if (hash.includes('access_token=') || hash.includes('error=')) {
      if (window.location.pathname !== '/auth') {
        navigate('/auth', { replace: true });
      }
    }
  }
  return null;
}
