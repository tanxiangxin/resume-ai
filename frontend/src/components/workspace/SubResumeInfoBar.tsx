import { Pencil, Trash2 } from "lucide-react";
import type { SubResume } from "../../types/workspace";
import { getScoreColorClass } from "../../lib/resume-insights";

interface SubResumeInfoBarProps {
  subResume: SubResume | null;
  onEdit: () => void;
  onDelete: () => void;
}

function formatDate(iso: string): string {
  return new Date(iso)
    .toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
    .replace(/\//g, "-");
}

export default function SubResumeInfoBar({
  subResume,
  onEdit,
  onDelete,
}: SubResumeInfoBarProps) {
  if (!subResume) {
    return (
      <div className="flex items-center justify-center px-4 py-3 border-b border-border">
        <span className="text-sm text-muted-foreground">未选择子简历</span>
      </div>
    );
  }

  const scoreColor =
    subResume.matchScore != null
      ? getScoreColorClass(subResume.matchScore)
      : null;
  const showRecommend =
    subResume.matchScore != null && subResume.matchScore >= 85;

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-border">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="text-base font-bold">
            {subResume.jobTitle || subResume.title}
          </span>
          {showRecommend && (
            <span className="bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-300 text-[10px] px-1.5 py-0.5 rounded">
              推荐
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>创建: {formatDate(subResume.createdAt)}</span>
          <span>更新: {formatDate(subResume.updatedAt)}</span>
          {scoreColor && (
            <span className={`${scoreColor.text} font-medium`}>
              匹配: {subResume.matchScore}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onEdit}
          className="flex items-center gap-1 border border-border rounded-lg px-2.5 py-1.5 text-[10px] hover:bg-accent transition-colors"
        >
          <Pencil className="w-3 h-3" />
          <span>编辑</span>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="flex items-center gap-1 border border-border rounded-lg px-2.5 py-1.5 text-[10px] hover:text-red-400 hover:border-red-500/30 hover:bg-red-500/10 transition-colors"
        >
          <Trash2 className="w-3 h-3" />
          <span>删除</span>
        </button>
      </div>
    </div>
  );
}
