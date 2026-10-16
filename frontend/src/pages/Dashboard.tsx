import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  FileText,
  LayoutTemplate,
  Loader2,
  Plus,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";
import WorkspaceCard from "../components/workspace/WorkspaceCard";
import CreateWorkspaceModal from "../components/workspace/CreateWorkspaceModal";
import {
  fetchWorkspaces,
  createWorkspace,
  deleteWorkspace,
  updateResume,
} from "../lib/api";
import type { Workspace } from "../types/workspace";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  const hhmm = date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  if (diffSec < 60) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟前`;
  if (diffHour < 24) return `${diffHour} 小时前`;
  if (diffDay === 1) return `昨天 ${hhmm}`;
  if (diffDay === 2) return `前天 ${hhmm}`;

  const mmdd = date
    .toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })
    .replace(/\//g, "-");
  return `${mmdd} ${hhmm}`;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setSearchQuery(value);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setDebouncedQuery(value), 300);
    },
    [],
  );

  const refreshWorkspaces = useCallback(async () => {
    try {
      const data = await fetchWorkspaces();
      setWorkspaces(data);
      setLoadError(false);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchWorkspaces()
      .then((data) => {
        if (!cancelled) setWorkspaces(data);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handler = () => {
      refreshWorkspaces();
    };
    window.addEventListener("global-sse-complete", handler);
    return () => {
      window.removeEventListener("global-sse-complete", handler);
    };
  }, [refreshWorkspaces]);

  const filteredWorkspaces = useMemo(() => {
    if (!debouncedQuery.trim()) return workspaces;
    const q = debouncedQuery.toLowerCase().trim();
    return workspaces.filter((ws) => ws.title.toLowerCase().includes(q));
  }, [workspaces, debouncedQuery]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div className="dashboard-page h-full overflow-y-auto">
      <div className="dashboard-content mx-auto max-w-[1440px]">
        <header className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-primary" />
            你的求职工作台
          </div>
          <span className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
            RESUME AI / 职业新起点
          </span>
        </header>

        <section className="workspace-hero mb-8 grid gap-8 rounded-3xl border border-border p-6 sm:p-9 lg:grid-cols-[1fr_280px]">
          <div className="relative z-10">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-card/80 px-3 py-1 text-xs font-medium text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              让每一份经历，被看见
            </span>
              <h1 className="mt-5 mb-4 text-2xl sm:text-4xl font-bold leading-tight tracking-tight text-foreground">
              下一份理想工作，
              <br />
              从一份好简历开始。
            </h1>
            <p className="max-w-lg text-sm leading-7 text-muted-foreground">
              整理你的经历，用 AI
              找到与岗位的契合点。简历、求职信与面试准备，都在这里有序展开。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setCreateModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                <Plus className="h-4 w-4" />
                新建工作空间
              </button>
              <button
                type="button"
                onClick={() => navigate("/templates")}
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-card/80 px-5 py-3 text-sm font-medium text-foreground transition-colors hover:bg-card"
              >
                探索简历模板
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="hero-resume hidden lg:block" aria-hidden="true">
            <div className="hero-paper">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-secondary" />
                <div>
                  <div className="h-2.5 w-20 rounded-full bg-primary/60" />
                  <div className="mt-2 h-1.5 w-28 rounded-full bg-border" />
                </div>
              </div>
              {[0, 1, 2].map((item) => (
                <div key={item} className="mt-6">
                  <div className="mb-3 h-2 w-16 rounded-full bg-primary/35" />
                  <div className="space-y-2">
                    <div className="h-1.5 rounded-full bg-border" />
                    <div className="h-1.5 w-4/5 rounded-full bg-border" />
                    <div className="h-1.5 w-3/5 rounded-full bg-border" />
                  </div>
                </div>
              ))}
            </div>
            <div className="hero-note">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>让经历更有说服力</span>
            </div>
          </div>
        </section>

        <section
          aria-label="工作空间概览"
          className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3"
        >
          {[
            {
              label: "工作空间",
              value: workspaces.length,
              icon: FileText,
              hint: "按职业方向整理经历",
            },
            {
              label: "岗位子简历",
              value: workspaces.reduce(
                (sum, ws) => sum + ws.subResumeIds.length,
                0,
              ),
              icon: LayoutTemplate,
              hint: "为每个机会量身定制",
            },
            {
              label: "AI 求职助手",
              value: "随时就绪",
              icon: Sparkles,
              hint: "润色 · 岗位分析 · 面试准备",
            },
          ].map(({ label, value, icon: Icon, hint }) => (
            <div
              key={label}
              className="flex items-center gap-4 rounded-2xl border border-border bg-card px-5 py-5"
            >
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-secondary text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-1 text-xl font-semibold text-foreground">
                  {loading || loadError ? "—" : value}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p>
              </div>
            </div>
          ))}
        </section>

        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="m-0 text-xl font-semibold text-foreground">
              我的工作空间
            </h2>
            <p className="mt-2 text-xs text-muted-foreground">
              从一份主简历出发，为不同岗位准备不同版本。
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex w-full sm:w-64 items-center gap-2 rounded-xl border border-border bg-card px-3 py-2.5 focus-within:ring-2 focus-within:ring-primary/20">
              <Search className="w-4 h-4 text-muted-foreground shrink-0" />
              <input
                type="text"
                placeholder="搜索工作空间..."
                aria-label="搜索工作空间"
                value={searchQuery}
                onChange={handleSearchChange}
                className="bg-transparent text-foreground text-sm outline-none placeholder:text-muted-foreground min-w-0 flex-1"
              />
              {searchQuery && (
                <button
                  type="button"
                  aria-label="清空搜索"
                  onClick={() => {
                    setSearchQuery("");
                    setDebouncedQuery("");
                  }}
                  className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {loading ? (
          <div
            role="status"
            className="flex justify-center gap-2 py-16 text-sm text-muted-foreground"
          >
            <Loader2 className="h-5 w-5 animate-spin" />
            正在整理你的工作空间...
          </div>
        ) : loadError ? (
          <div
            role="alert"
            className="rounded-2xl border border-border bg-card p-10 text-center"
          >
            <p className="text-sm text-foreground">暂时无法加载工作空间</p>
            <p className="mt-2 text-xs text-muted-foreground">
              请确认后端服务已启动，然后重试。
            </p>
            <button
              type="button"
              onClick={() => void refreshWorkspaces()}
              className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground"
            >
              重新加载
            </button>
          </div>
        ) : filteredWorkspaces.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-primary/25 bg-card p-10 text-center">
            <FileText className="mx-auto mb-4 h-9 w-9 text-primary/60" />
            <h3 className="text-base font-semibold text-foreground">
              {debouncedQuery
                ? "没有找到匹配的工作空间"
                : "为下一个机会，留一页空白"}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {debouncedQuery
                ? "换一个关键词试试。"
                : "导入已有简历，或选择喜欢的模板开始。"}
            </p>
            {!debouncedQuery && (
              <button
                type="button"
                onClick={() => setCreateModalOpen(true)}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm text-primary-foreground"
              >
                <Plus className="h-4 w-4" />
                创建第一个工作空间
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 pb-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {filteredWorkspaces.map((ws) => (
              <WorkspaceCard
                key={ws.id}
                id={ws.id}
                title={ws.title}
                domain={`${ws.template} 模板`}
                subResumeIds={ws.subResumeIds}
                lastModified={formatRelativeTime(ws.updatedAt)}
                templateName={ws.template}
                isActive={ws.isDefault}
                onClick={() => navigate(`/workspace/${ws.id}`)}
                onDelete={async (id) => {
                  try {
                    await deleteWorkspace(id);
                    toast.success("工作空间已删除");
                    refreshWorkspaces();
                  } catch (err: unknown) {
                    toast.error(
                      err instanceof Error ? err.message : "删除失败",
                    );
                  }
                }}
                onRename={async (id, newTitle) => {
                  try {
                    await updateResume({ id, title: newTitle });
                    toast.success("重命名成功");
                    refreshWorkspaces();
                  } catch (err: unknown) {
                    toast.error(
                      err instanceof Error ? err.message : "重命名失败",
                    );
                  }
                }}
              />
            ))}
          </div>
        )}
        <p className="mt-8 mb-2 text-center text-[11px] text-muted-foreground">
          每一次认真准备，都离理想更近一步。
        </p>
      </div>

      <CreateWorkspaceModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onRefreshWs={refreshWorkspaces}
        onCreate={async (template, name) => {
          const newWs = await createWorkspace(template, name || undefined);
          setWorkspaces((prev) => [...prev, newWs]);
          setCreateModalOpen(false);
        }}
      />
    </div>
  );
}
