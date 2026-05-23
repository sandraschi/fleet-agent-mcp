import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "@/components/layout/app-layout";
import { Dashboard } from "@/pages/dashboard";
import { ChatPage } from "@/pages/chat";
import { Help } from "@/pages/help";
import { Tools } from "@/pages/tools";
import { SettingsPage } from "@/pages/settings";
import { LoggerPage } from "@/pages/logger";
import { Status } from "@/pages/status";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/help" element={<Help />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/logs" element={<LoggerPage />} />
          <Route path="/status" element={<Status />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}

export default App;
