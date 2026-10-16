import { useMemo } from 'react';
import { BarChart3, Check, EyeOff } from 'lucide-react';
import type { ResumeSection } from '../../types/resume';
import {
  calculateHealthScore,
  getScoreColorClass,
  getTextContent,
} from '../../lib/resume-insights';

interface ResumeInsightsPanelProps {
  sections: ResumeSection[];
}

export default function ResumeInsightsPanel({ sections }: ResumeInsightsPanelProps) {
  const healthResult = useMemo(() => calculateHealthScore(sections), [sections]);

  const visibleSections = useMemo(() => sections.filter((s) => s.visible), [sections]);
  const hiddenSections = useMemo(() => sections.filter((s) => !s.visible), [sections]);

  const sectionWordData = useMemo(() => {
    return visibleSections.map((s) => ({
      section: s,
      wordCount: getTextContent(s).trim().length,
    }));
  }, [visibleSections]);

  const maxWordCount = useMemo(
    () => Math.max(...sectionWordData.map((d) => d.wordCount), 1),
    [sectionWordData],
  );

  const scoreColor = getScoreColorClass(healthResult.score);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-3.5 h-3.5 text-primary" />
          <span className="text-xs font-semibold">简历洞察</span>
        </div>
        <span className="text-[10px] text-muted-foreground">
          {visibleSections.length} 个可见 Section
        </span>
      </div>

      <div className="flex items-center gap-4 mb-4 p-3 rounded-lg bg-background/50">
        <div className="relative w-14 h-14 flex items-center justify-center">
          <svg className="w-14 h-14 -rotate-90" viewBox="0 0 36 36">
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#262626"
              strokeWidth={3}
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="#f472b6"
              strokeWidth={3}
              strokeDasharray={`${healthResult.score}, 100`}
              strokeLinecap="round"
              className="transition-all duration-700"
            />
          </svg>
          <span className="absolute text-sm font-bold">{healthResult.score}</span>
        </div>
        <div className="flex-1">
          <div className="text-xs font-medium mb-1">综合健康度</div>
          <div className="text-[10px] text-muted-foreground">
            {healthResult.filledCount} 个可见 · {healthResult.totalWords} 字 ·{' '}
            {healthResult.filledCount < healthResult.visibleCount
              ? `${healthResult.visibleCount - healthResult.filledCount} 个待完善`
              : '全部完善'}
          </div>
          <div className="mt-1.5 h-1.5 bg-background rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${scoreColor.barFrom} ${scoreColor.barTo} transition-all duration-700`}
              style={{ width: `${healthResult.score}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
          Section 分布
        </div>
        <div className="space-y-1">
          {sectionWordData.map(({ section: s, wordCount }) => {
            const barWidth = maxWordCount > 0 ? (wordCount / maxWordCount) * 100 : 0;
            return (
              <div key={s.id} className="px-1.5 py-1">
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <div className="flex items-center gap-1.5">
                    <Check className="w-3 h-3 text-green-400" strokeWidth={2} />
                    <span>{s.title}</span>
                  </div>
                  <span className="text-muted-foreground">{wordCount}字</span>
                </div>
                <div className="h-1 bg-background rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-green-500/60"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
          {hiddenSections.length > 0 && (
            <div className="pt-1 border-t border-border/50 px-1.5">
              {hiddenSections.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between text-[10px] opacity-40"
                >
                  <div className="flex items-center gap-1.5">
                    <EyeOff className="w-3 h-3 text-muted-foreground" strokeWidth={2} />
                    <span>{s.title}</span>
                  </div>
                  <span>已隐藏</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
