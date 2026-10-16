import MasterResumeCard from "./MasterResumeCard";
import SubResumeList from "./SubResumeList";
import { FileText, PanelLeftOpen, PanelLeftClose, Plus } from "lucide-react";
import type { Workspace, SubResume } from "../../types/workspace";
import type { ResumeSection } from "../../types/resume";

interface WorkspaceSidebarProps {
  workspace: Workspace;
  sections: ResumeSection[];
  subResumes: SubResume[];
  selectedSubResumeId: string | null;
  onSelectSubResume: (id: string) => void;
  onCreateNew: () => void;
  onEditMasterResume: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  loading?: boolean;
}

export default function WorkspaceSidebar({
  workspace,
  sections,
  subResumes,
  selectedSubResumeId,
  onSelectSubResume,
  onCreateNew,
  onEditMasterResume,
  collapsed,
  onToggleCollapse,
  loading,
}: WorkspaceSidebarProps) {
  const workspaceInitial = workspace.title.charAt(0).toUpperCase();

  if (collapsed) {
    return (
      <div className="w-12 shrink-0 flex flex-col items-center h-full border-r border-border bg-card">
        <button
          onClick={onToggleCollapse}
          className="w-full h-12 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors cursor-pointer"
          aria-label="展开侧边栏"
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>

        <div className="flex-1 flex flex-col items-center pt-4">
          <div
            className="w-8 h-8 rounded-md bg-muted text-muted-foreground flex items-center justify-center text-xs font-semibold"
            title={workspace.title}
            aria-label={`工作空间：${workspace.title}`}
          >
            {workspaceInitial}
          </div>

          <div className="my-3 h-px w-5 bg-border" />

          <button
            onClick={onEditMasterResume}
            className="w-8 h-8 rounded-md bg-primary/10 text-primary flex items-center justify-center hover:bg-primary hover:text-primary-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors cursor-pointer"
            title="编辑主简历"
            aria-label="编辑主简历"
          >
            <FileText className="w-4 h-4" />
          </button>

          {subResumes.length > 0 && (
            <div className="flex flex-col items-center gap-1.5 mt-3 pt-3 border-t border-border">
              {subResumes.map((resume) => {
                const isSelected = resume.id === selectedSubResumeId;
                const initial = resume.title.charAt(0).toUpperCase();
                return (
                  <button
                    key={resume.id}
                    onClick={() => onSelectSubResume(resume.id)}
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-medium transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-emerald-500 text-white"
                        : "bg-muted text-muted-foreground hover:bg-muted/70"
                    }`}
                    title={resume.title}
                  >
                    {initial}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 底部新建按钮 */}
        <div className="pb-3">
          <button
            onClick={onCreateNew}
            className="w-7 h-7 rounded-full flex items-center justify-center bg-muted text-muted-foreground hover:bg-primary hover:text-primary-foreground transition-colors cursor-pointer"
            aria-label="新建子简历"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-[260px] shrink-0 flex flex-col h-full border-r border-border bg-card">
      {/* Header: workspace title + collapse */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-6 h-6 rounded-md bg-muted text-muted-foreground flex items-center justify-center text-[11px] font-semibold shrink-0">
            {workspaceInitial}
          </div>
          <span className="text-sm font-medium text-foreground truncate">
            {workspace.title}
          </span>
        </div>
        <button
          onClick={onToggleCollapse}
          className="shrink-0 w-7 h-7 flex items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors cursor-pointer"
          aria-label="收起侧边栏"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Master Resume Section */}
        <div className="px-3 pt-3">
          <MasterResumeCard
            workspace={workspace}
            sections={sections}
            onEdit={onEditMasterResume}
          />
        </div>

        {/* Sub Resume Section */}
        <div className="px-3 pt-4 pb-3">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
              职位定制简历
            </span>
            <span className="text-[11px] text-muted-foreground/60 tabular-nums">
              {subResumes.length}
            </span>
          </div>

          <SubResumeList
            subResumes={subResumes}
            selectedId={selectedSubResumeId}
            onSelect={onSelectSubResume}
            onCreateNew={onCreateNew}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
