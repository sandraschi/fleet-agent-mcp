import { Link, useLocation } from "react-router-dom";
import { cn } from "@/common/utils";
import {
  LayoutDashboard,
  HelpCircle,
  Activity,
  GitBranch,
  Bot,
  Settings2,
  Terminal,
  Brain,
  TrendingUp,
  ListChecks,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: Bot },
  { href: "/tasks", label: "Tasks", icon: ListChecks },
  { href: "/memory", label: "Memory", icon: Brain },
  { href: "/evolution", label: "Evolution", icon: TrendingUp },
  { href: "/help", label: "Help", icon: HelpCircle },
  { href: "/tools", label: "Tools", icon: GitBranch },
  { href: "/settings", label: "Settings", icon: Settings2 },
  { href: "/logs", label: "Logger", icon: Terminal },
  { href: "/status", label: "Status", icon: Activity },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const activePath = location.pathname;

  return (
    <aside
      className={cn(
        "relative flex flex-col border-r border-slate-800 bg-slate-950/80 transition-all duration-300",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex h-14 items-center border-b border-slate-800 px-4">
        <div className="flex items-center gap-2 font-semibold text-slate-100">
          <span className="text-lg">🌸</span>
          {!collapsed && <span>fleet-agent</span>}
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = activePath === item.href;
          return (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-slate-800 hover:text-white",
                isActive ? "bg-slate-800 text-white" : "text-slate-400",
                collapsed ? "justify-center" : "justify-start"
              )}
            >
              <item.icon className={cn("h-5 w-5 shrink-0", !collapsed && "mr-3", isActive && "text-fleet-400")} />
              {!collapsed && <span>{item.label}</span>}
              {collapsed && (
                <span className="absolute left-full ml-2 hidden rounded bg-slate-800 px-2 py-1 text-xs text-white group-hover:block z-50 whitespace-nowrap">
                  {item.label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 p-2">
        <div className="px-3 pb-2">
          {!collapsed && (
            <p className="text-[10px] text-slate-600 leading-tight">
              Inspired by<br />
              <a href="https://github.com/kagura-agent" target="_blank" rel="noopener noreferrer" className="text-fleet-700 hover:text-fleet-500">kagura-agent</a>
              <br />887+ PRs, 52 repos
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-md p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <span className="flex items-center w-full">
              <ChevronLeft className="h-5 w-5 mr-2" />
              Collapse
            </span>
          )}
        </button>
      </div>
    </aside>
  );
}
