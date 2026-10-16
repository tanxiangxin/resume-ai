import { FileText, Pencil } from "lucide-react";
import type { Workspace } from "../../types/workspace";
import type { ResumeSection } from "../../types/resume";

interface MasterResumeCardProps {
  workspace: Workspace;
  sections: ResumeSection[];
  onEdit: () => void;
}

export default function MasterResumeCard({
  workspace,
  sections,
  onEdit,
}: MasterResumeCardProps) {
  const visibleSectionCount = sections.filter((s) => s.visible).length;

  return (
    <button
      onClick={onEdit}
      className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
      aria-label={`编辑主简历：${workspace.title}`}
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <FileText className="h-4 w-4" />
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">
          主简历
        </span>
        <span className="mt-0.5 block truncate text-[11px] text-muted-foreground">
          {visibleSectionCount} 个内容模块 · 全部经历与基础信息
        </span>
      </span>

      <span className="flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground transition-colors group-hover:text-foreground">
        编辑
        <Pencil className="h-3 w-3" />
      </span>
    </button>
  );
}
