import { useState, useEffect } from "react";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("fleet-sidebar-collapsed");
    if (stored !== null) setCollapsed(stored === "true");
  }, []);

  const handleToggle = () => {
    const newState = !collapsed;
    setCollapsed(newState);
    localStorage.setItem("fleet-sidebar-collapsed", String(newState));
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-50 font-sans">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar collapsed={collapsed} onToggle={handleToggle} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-6">
            <div className="mx-auto max-w-5xl">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
