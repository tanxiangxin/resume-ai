import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  FileText,
  Palette,
  Bell,
  Settings,
  Sparkles,
} from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { fetchErrorTasks } from "../../lib/api";
import {
  hasUnreadNotification,
  onNotificationChange,
  getNotificationTasks,
  getNotificationTasksAndClear,
  onNotificationTasksChange,
} from "../../lib/notification";
import type { WorkTask } from "../../types/work";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import MessageList from "./MessageDropdown";
import SettingsModal from "../settings/SettingsModal";
import logoSvg from "../../assets/logo.svg";

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [showSettings, setShowSettings] = useState(false);
  const [messagesOpen, setMessagesOpen] = useState(false);
  const [hasUnread, setHasUnread] = useState(false);
  const [localTasks, setLocalTasks] = useState<WorkTask[]>(() =>
    getNotificationTasksAndClear(),
  );

  const { data: errorTasks } = useQuery({
    queryKey: ["work-tasks", "error"],
    queryFn: fetchErrorTasks,
    refetchInterval: 15000,
  });

  useEffect(() => {
    return onNotificationChange(() => {
      setHasUnread(hasUnreadNotification());
    });
  }, []);

  useEffect(() => {
    return onNotificationTasksChange(() => {
      setLocalTasks(getNotificationTasks());
    });
  }, []);

  const tasks = useMemo(() => {
    const errors = errorTasks || [];
    const taskMap = new Map<string, WorkTask>();
    for (const t of errors) taskMap.set(t.id, t);
    for (const t of localTasks) {
      if (!taskMap.has(t.id)) {
        taskMap.set(t.id, t);
      }
    }
    return Array.from(taskMap.values()).sort((a, b) => {
      const aTime = a.createdAt ? new Date(a.createdAt).getTime() : 0;
      const bTime = b.createdAt ? new Date(b.createdAt).getTime() : 0;
      return bTime - aTime;
    });
  }, [errorTasks, localTasks]);

  const getMetaString = (
    meta: WorkTask["metaInfo"],
    ...keys: Array<keyof NonNullable<WorkTask["metaInfo"]>>
  ): string | undefined => {
    if (!meta) return undefined;
    for (const key of keys) {
      const value = meta[key];
      if (typeof value === "string" && value.trim()) {
        return value;
      }
    }
    return undefined;
  };

  const handleTaskClick = (task: WorkTask) => {
    const workspaceId =
      task.workspaceId ||
      getMetaString(task.metaInfo, "workspaceId", "workspace_id");
    const resumeId = getMetaString(task.metaInfo, "resumeId", "resume_id");

    setMessagesOpen(false);
    if (
      (task.taskType === "jd_score" || task.taskType === "jd_parse") &&
      workspaceId &&
      resumeId
    ) {
      navigate(`/workspace/${workspaceId}/resumes/${resumeId}/jd`);
      return;
    }
    if (task.taskType === "greeting_generate" && workspaceId && resumeId) {
      navigate(`/workspace/${workspaceId}/resumes/${resumeId}/greeting`);
      return;
    }
    if (task.taskType === "cover_letter_generate" && workspaceId && resumeId) {
      navigate(`/workspace/${workspaceId}/resumes/${resumeId}/cover-letter`);
      return;
    }
    if (workspaceId) {
      navigate(`/workspace/${workspaceId}`);
      return;
    }
    navigate("/workspace");
  };

  const navItems = [
    { label: "工作空间", path: "/workspace", icon: FileText },
    { label: "模板库", path: "/templates", icon: Palette },
  ];

  return (
    <>
      <aside className="app-sidebar w-[76px] md:w-[232px] bg-card border-r border-border flex flex-col h-full shrink-0 overflow-hidden">
        <div className="h-24 flex items-center justify-center md:justify-start md:px-6 shrink-0 gap-3">
          <button
            type="button"
            onClick={() => navigate("/workspace")}
            aria-label="Resume AI 首页"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          >
            <img src={logoSvg} alt="" className="w-10 h-10 shrink-0" />
            <div className="hidden md:block text-left">
              <span className="text-foreground font-bold text-lg whitespace-nowrap">
                Resume AI
              </span>
              <p className="mt-0.5 text-[10px] tracking-[0.16em] text-muted-foreground">
                YOUR CAREER STUDIO
              </p>
            </div>
          </button>
        </div>

        <nav
          aria-label="主导航"
          className="flex-1 p-3 md:px-4 flex flex-col min-h-0"
        >
          <p className="hidden md:block mb-3 px-3 text-[10px] font-medium tracking-widest text-muted-foreground">
            创作与准备
          </p>
          <ul className="space-y-1">
            {navItems.map(({ label, path, icon: Icon }) => {
              const isActive = location.pathname.startsWith(path);
              return (
                <li key={path}>
                  <button
                    type="button"
                    onClick={() => navigate(path)}
                    title={label}
                    aria-current={isActive ? "page" : undefined}
                    className={`w-full flex items-center justify-center md:justify-start gap-3 px-3 py-3 rounded-xl transition-colors ${
                      isActive
                        ? "text-primary bg-secondary font-semibold"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 shrink-0 ${isActive ? "text-primary" : ""}`}
                    />
                    <span className="hidden md:inline text-sm whitespace-nowrap">
                      {label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="mt-auto pt-6 space-y-1">
            <div className="sidebar-tip hidden md:block mb-6 rounded-2xl border border-border p-4">
              <Sparkles className="mb-3 h-5 w-5 text-primary" />
              <p className="text-sm font-semibold text-foreground">
                好经历，值得好表达
              </p>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                从模板开始，把你的下一步写得更清晰。
              </p>
              <button
                type="button"
                onClick={() => navigate("/templates")}
                className="mt-3 flex items-center gap-1 text-xs font-semibold text-primary"
              >
                发现适合你的模板
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </div>
            <Popover
              open={messagesOpen}
              onOpenChange={(open) => {
                setMessagesOpen(open);
                if (open) setHasUnread(false);
              }}
            >
              <PopoverTrigger asChild>
                <button
                  type="button"
                  aria-label="通知"
                  className="w-full flex items-center justify-center md:justify-start gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                >
                  <span className="relative shrink-0">
                    <Bell className="w-4 h-4" />
                    {hasUnread && (
                      <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-teal-500 rounded-full" />
                    )}
                  </span>
                  <span className="hidden md:inline text-sm whitespace-nowrap">
                    通知
                  </span>
                </button>
              </PopoverTrigger>
              <PopoverContent
                side="right"
                align="start"
                sideOffset={12}
                className="w-[min(24rem,calc(100vw-6rem))] p-0 bg-card rounded-xl border border-border shadow-lg"
              >
                <MessageList tasks={tasks} onTaskClick={handleTaskClick} />
              </PopoverContent>
            </Popover>

            <button
              type="button"
              onClick={() => setShowSettings(true)}
              aria-label="设置"
              className="w-full flex items-center justify-center md:justify-start gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            >
              <Settings className="w-4 h-4 shrink-0" />
              <span className="hidden md:inline text-sm whitespace-nowrap">
                设置
              </span>
            </button>
          </div>
        </nav>
        <div className="hidden md:flex items-center gap-3 border-t border-border px-6 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-primary">
            ME
          </div>
          <div>
            <p className="text-xs font-medium text-foreground">我的求职空间</p>
            <p className="mt-1 text-[10px] text-muted-foreground">
              把准备，变成机会
            </p>
          </div>
        </div>
      </aside>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </>
  );
}
