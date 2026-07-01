import { AppLayout } from "@/components/layout/app-layout";
import { ChatPage } from "@/pages/chat";
import { ContributionsPage } from "@/pages/contributions";
import { Dashboard } from "@/pages/dashboard";
import { Evolution } from "@/pages/evolution";
import { Help } from "@/pages/help";
import { LoggerPage } from "@/pages/logger";
import { Memory } from "@/pages/memory";
import { ScriptsPage } from "@/pages/scripts";
import { SettingsPage } from "@/pages/settings";
import { Status } from "@/pages/status";
import { Tasks } from "@/pages/tasks";
import { Tools } from "@/pages/tools";
import {
	Navigate,
	Route,
	BrowserRouter as Router,
	Routes,
} from "react-router-dom";

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
					<Route path="/scripts" element={<ScriptsPage />} />
					<Route path="/logs" element={<LoggerPage />} />
					<Route path="/status" element={<Status />} />
					<Route path="/contributions" element={<ContributionsPage />} />
					<Route path="/memory" element={<Memory />} />
					<Route path="/evolution" element={<Evolution />} />
					<Route path="/tasks" element={<Tasks />} />
					<Route path="*" element={<Navigate to="/" replace />} />
				</Routes>
			</AppLayout>
		</Router>
	);
}

export default App;
