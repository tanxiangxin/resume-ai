import type { SubResume } from "../../types/workspace";
import { getScoreColorClass } from "../../lib/resume-insights";
import { Plus } from "lucide-react";

interface SubResumeListProps {
  subResumes: SubResume[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreateNew: () => void;
  loading?: boolean;
}

export default function SubResumeList({
  subResumes,
  selectedId,
  onSelect,
  onCreateNew,
  loading,
}: SubResumeListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center text-muted-foreground py-8 text-sm">
        加载中...
      </div>
    );
  }

  const isEmpty = subResumes.length === 0;

  return (
    <div className="space-y-0.5">
      {isEmpty ? (
        <button
          onClick={onCreateNew}
          className="w-full rounded-lg py-3 flex items-center justify-center gap-2 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm">新建子简历</span>
        </button>
      ) : (
        <>
          {subResumes.map((resume) => {
            const isSelected = resume.id === selectedId;
            const scoreColor =
              resume.matchScore !== undefined
                ? getScoreColorClass(resume.matchScore)
                : null;

            return (
              <button
                key={resume.id}
                onClick={() => onSelect(resume.id)}
                className={`w-full text-left rounded-lg px-3 py-2 cursor-pointer transition-colors group ${
                  isSelected ? "bg-muted" : "hover:bg-muted/50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[13px] font-medium truncate text-foreground">
                        {resume.title}
                      </span>
                      {resume.matchScore !== undefined &&
                        resume.matchScore >= 85 && (
                          <span className="bg-muted text-muted-foreground text-[10px] font-medium px-1.5 py-px rounded shrink-0">
                            推荐
                          </span>
                        )}
                    </div>
                    {resume.jobTitle && (
                      <p className="text-[11px] mt-0.5 truncate text-muted-foreground">
                        {resume.jobTitle}
                      </p>
                    )}
                  </div>
                  {scoreColor && (
                    <span
                      className={`text-[11px] font-semibold tabular-nums shrink-0 ${scoreColor.text}`}
                    >
                      {resume.matchScore}
                    </span>
                  )}
                </div>
              </button>
            );
          })}

          <button
            onClick={onCreateNew}
            className="w-full rounded-lg py-2 flex items-center justify-center gap-1.5 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer mt-1"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="text-xs">新建子简历</span>
          </button>
        </>
      )}
    </div>
  );
}
