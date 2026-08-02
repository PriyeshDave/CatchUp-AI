import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider, useSession } from "./context/SessionContext.jsx";
import Login from "./pages/Login.jsx";
import CopilotHome from "./pages/CopilotHome.jsx";
import MeetingWorkspace from "./pages/MeetingWorkspace.jsx";
import SystemFlow from "./pages/SystemFlow.jsx";
import AppShell from "./components/AppShell.jsx";

function RequireSession({ children }) {
  const { session } = useSession();
  if (!session) return <Navigate to="/login" replace />;
  return children;
}

function Routed() {
  const { session } = useSession();
  return (
    <Routes>
      <Route path="/login" element={session ? <Navigate to="/" replace /> : <Login />} />
      <Route
        path="/"
        element={
          <RequireSession>
            <AppShell>
              <CopilotHome />
            </AppShell>
          </RequireSession>
        }
      />
      <Route
        path="/meeting/:meetingId"
        element={
          <RequireSession>
            <AppShell>
              <MeetingWorkspace />
            </AppShell>
          </RequireSession>
        }
      />
      <Route
        path="/meeting/:meetingId/system-flow"
        element={
          <RequireSession>
            <AppShell>
              <SystemFlow />
            </AppShell>
          </RequireSession>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <SessionProvider>
      <HashRouter>
        <Routed />
      </HashRouter>
    </SessionProvider>
  );
}
