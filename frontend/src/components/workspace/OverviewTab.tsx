import { useMemo, useEffect } from "react";
import {
  FileText,
  Users,
  CheckCircle2,
  AlertCircle,
  Star,
  Clock,
  Key,
  Pencil,
  Lightbulb,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { JdAnalysis } from "../../types/workspace";
import { getScoreColorClass, fmtDateTime } from "../../lib/resume-insights";
import { enrichJdAnalysis } from "../../lib/jd-analysis-adapter";
import { useInterviewStore } from "@/stores/interview-store";
import type { InterviewStatus } from "@/types/interview";
import {
  typography,
  card,
  icon as iconSizes,
  emptyState,
} from "../../lib/component-styles";
import ScoreRing from "./ScoreRing";

interface OverviewTabProps {
  analyses: JdAnalysis[];
  subResumeId: string;
  onViewInterview: (collectionId?: string) => void;
}

// Helper to render lucide icons for suggestions based on type
const getSuggestionIcon = (type: string): any => {
  switch (type) {
    case "keyword_add":
      return <Key className="w-3 h-3 text-muted-foreground" />;
    case "wording":
      return <Pencil className="w-3 h-3 text-muted-foreground" />;
    default:
      return <Lightbulb className="w-3 h-3 text-muted-foreground" />;
  }
};

export default function OverviewTab({
  analyses,
  subResumeId,
  onViewInterview,
}: OverviewTabProps) {
  const currentAnalysis = useMemo(() => {
    if (!analyses.length) return null;
    const latest = analyses[0];
    return enrichJdAnalysis(latest);
  }, [analyses]);

  const keywordMatchesArr = useMemo(() => {
    if (!currentAnalysis?.keywordMatches) return [];
    return Array.isArray(currentAnalysis.keywordMatches) &&
      typeof currentAnalysis.keywordMatches[0] === "object"
      ? (currentAnalysis.keywordMatches as any[])
      : [];
  }, [currentAnalysis]);

  const partialMatchesArr = useMemo(() => {
    return currentAnalysis?.partialMatches || [];
  }, [currentAnalysis]);

  const missingKeywordsArr = useMemo(() => {
    if (!currentAnalysis?.missingKeywords) return [];
    return Array.isArray(currentAnalysis.missingKeywords) &&
      typeof currentAnalysis.missingKeywords[0] === "object"
      ? (currentAnalysis.missingKeywords as any[])
      : [];
  }, [currentAnalysis]);

  const skillMatchesArr = useMemo(() => {
    return currentAnalysis?.skillMatches || [];
  }, [currentAnalysis]);

  const strengthsArr = useMemo(() => {
    return currentAnalysis?.strengths || [];
  }, [currentAnalysis]);

  const suggestionsArr = useMemo(() => {
    return (currentAnalysis?.suggestions as any[]) || [];
  }, [currentAnalysis]);

  const historyAnalyses = useMemo(() => {
    return analyses.map((a, idx) => ({
      ...a,
      version: a.version || analyses.length - idx,
      isLatest: idx === 0,
    }));
  }, [analyses]);

  const interviewCollections = useInterviewStore((s) => s.collections);
  const fetchCollections = useInterviewStore((s) => s.fetchCollections);

  useEffect(() => {
    if (subResumeId) {
      fetchCollections(subResumeId);
    }
  }, [subResumeId, fetchCollections]);

  const getStatusColor = (status: InterviewStatus): string => {
    const colors: Record<InterviewStatus, string> = {
      completed:
        "text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-500/15 border border-green-300 dark:border-green-500/30",
      in_progress: "text-blue-400 bg-blue-500/10 border border-blue-500/20",
      not_started: "text-muted-foreground bg-muted/30 border border-border",
    };
    return colors[status] || colors.not_started;
  };

  const getStatusLabel = (status: InterviewStatus): string => {
    const labels: Record<InterviewStatus, string> = {
      completed: "已完成",
      in_progress: "进行中",
      not_started: "待开始",
    };
    return labels[status] || status;
  };

  const requirementTotal =
    currentAnalysis?.totalRequirements ||
    keywordMatchesArr.length +
      partialMatchesArr.length +
      missingKeywordsArr.length;
  const completedInterviewCount = interviewCollections.filter(
    (c) => c.status === "completed",
  ).length;
  const interviewRoundTotal = interviewCollections.reduce(
    (sum, c) => sum + c.rounds.length,
    0,
  );
  const interviewRoundCompleted = interviewCollections.reduce(
    (sum, c) => sum + c.rounds.filter((r) => r.status === "completed").length,
    0,
  );
  const topSuggestions = [...suggestionsArr].sort((a: any, b: any) => {
    const priority = { high: 3, medium: 2, low: 1 };
    return (
      (priority[b.priority as keyof typeof priority] || 0) -
      (priority[a.priority as keyof typeof priority] || 0)
    );
  });

  return (
    <div className="grid h-full min-w-0 grid-cols-[minmax(0,1fr)_320px] gap-4 overflow-hidden fade-in">
      <div className="min-w-0 space-y-4 overflow-y-auto pr-1">
        <div className={`${card.base} overflow-hidden`}>
          {currentAnalysis ? (
            <>
              <div className="grid grid-cols-[132px_minmax(0,1fr)]">
                <div className="flex items-center justify-center border-r border-border bg-muted/30 p-5">
                  <ScoreRing
                    score={currentAnalysis.overallScore}
                    label="总体匹配"
                  />
                </div>
                <div className="min-w-0 p-5">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3
                      className={`${typography.heading.md} flex items-center gap-2`}
                    >
                      <FileText
                        className={`${iconSizes.md} text-muted-foreground`}
                      />
                      最新 JD 结论
                    </h3>
                    <span className={typography.caption.md}>
                      v{currentAnalysis.version} ·{" "}
                      {fmtDateTime(currentAnalysis.createdAt)}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-muted-foreground break-all">
                    {currentAnalysis.summary}
                  </p>
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="text-[11px] text-muted-foreground">
                        完全匹配
                      </div>
                      <div className="mt-1 text-lg font-semibold text-green-600 dark:text-green-400">
                        {keywordMatchesArr.length}
                        <span className="ml-1 text-[10px] font-normal text-muted-foreground">
                          /{requirementTotal || 0}
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="text-[11px] text-muted-foreground">
                        部分匹配
                      </div>
                      <div className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">
                        {partialMatchesArr.length}
                        <span className="ml-1 text-[10px] font-normal text-muted-foreground">
                          /{requirementTotal || 0}
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="text-[11px] text-muted-foreground">
                        缺失
                      </div>
                      <div className="mt-1 text-lg font-semibold text-red-600 dark:text-red-400">
                        {missingKeywordsArr.length}
                        <span className="ml-1 text-[10px] font-normal text-muted-foreground">
                          /{requirementTotal || 0}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
              <Star className="w-8 h-8 opacity-20" />
              <p className="text-xs">暂无评分数据</p>
              <p className="text-[10px] opacity-60">请先对子简历进行 JD 评分</p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className={`${card.base} p-5`}>
            <h3
              className={`${typography.heading.md} mb-4 flex items-center gap-2`}
            >
              <CheckCircle2 className={`${iconSizes.md} text-green-500`} />
              候选优势
            </h3>
            {strengthsArr.length > 0 ? (
              <div className="space-y-3">
                {strengthsArr.slice(0, 4).map((s, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
                    <span className="text-xs leading-relaxed text-muted-foreground break-all">
                      {s.description}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className={typography.caption.md}>暂无优势分析</p>
            )}
          </div>

          <div className={`${card.base} p-5`}>
            <h3
              className={`${typography.heading.md} mb-4 flex items-center gap-2`}
            >
              <AlertCircle className={`${iconSizes.md} text-amber-500`} />
              优先处理
            </h3>
            {topSuggestions.length > 0 ? (
              <div className="space-y-3">
                {topSuggestions.slice(0, 4).map((s, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0">
                      {getSuggestionIcon(s.type)}
                    </span>
                    <span className="text-xs leading-relaxed text-muted-foreground break-all">
                      {s.rationale}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className={typography.caption.md}>暂无改进建议</p>
            )}
          </div>
        </div>

        {historyAnalyses.length > 0 && (
          <div className={`${card.base} p-5`}>
            <h3
              className={`${typography.heading.md} mb-4 flex items-center gap-2`}
            >
              <Clock className={`${iconSizes.md} text-muted-foreground`} />
              JD 评分趋势
            </h3>
            <div className="h-[160px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={[...historyAnalyses].reverse()}
                  margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="version"
                    tick={{ fontSize: 10, fill: "#888" }}
                    tickFormatter={(v) => `v${v}`}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 10, fill: "#888" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const d = payload[0].payload;
                        const c = getScoreColorClass(d.overallScore);
                        return (
                          <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg max-w-[220px]">
                            <div className="text-[10px] text-muted-foreground mb-0.5">
                              v{d.version} · {fmtDateTime(d.createdAt)}
                            </div>
                            <div className={`text-xs font-bold ${c.text} mb-1`}>
                              {d.overallScore}%
                            </div>
                            {d.summary && (
                              <div className="text-[10px] text-muted-foreground leading-snug line-clamp-3 break-words">
                                {d.summary}
                              </div>
                            )}
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="overallScore"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={(props: any) => {
                      const { cx, cy, payload } = props;
                      const isLatest = payload.isLatest;
                      return (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isLatest ? 4 : 3}
                          fill={
                            isLatest
                              ? "hsl(var(--primary))"
                              : "hsl(var(--background))"
                          }
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                        />
                      );
                    }}
                    activeDot={{
                      r: 5,
                      fill: "hsl(var(--primary))",
                      stroke: "hsl(var(--background))",
                      strokeWidth: 2,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        <div className={`${card.base} p-5`}>
          <h3
            className={`${typography.heading.md} mb-4 flex items-center gap-2`}
          >
            <Star className={`${iconSizes.md} text-yellow-400`} />
            关键技能匹配
          </h3>
          {skillMatchesArr.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {skillMatchesArr.map((s, idx) => {
                const c = getScoreColorClass(s.matchScore);
                return (
                  <div key={idx}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs break-all">{s.skill}</span>
                      <span className={`text-xs font-bold ${c.text}`}>
                        {s.matchScore}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${c.barFrom} ${c.barTo} rounded-full transition-all duration-700`}
                        style={{ width: `${s.matchScore}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[10px] text-muted-foreground opacity-60">
              暂无技能匹配数据
            </p>
          )}
        </div>
      </div>

      <aside className="space-y-4 overflow-y-auto">
        <div className={`${card.base} p-5`}>
          <h3
            className={`${typography.heading.md} mb-4 flex items-center gap-2`}
          >
            <Users className={`${iconSizes.md} text-muted-foreground`} />
            面试进度
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-border bg-background p-3">
              <div className="text-[10px] text-muted-foreground">方案完成</div>
              <div className="mt-1 text-base font-semibold tabular-nums">
                {completedInterviewCount}/{interviewCollections.length}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-background p-3">
              <div className="text-[10px] text-muted-foreground">轮次完成</div>
              <div className="mt-1 text-base font-semibold tabular-nums">
                {interviewRoundCompleted}/{interviewRoundTotal}
              </div>
            </div>
          </div>
        </div>

        {interviewCollections.length > 0 ? (
          <div className={`${card.base} p-5`}>
            <h3
              className={`${typography.heading.md} mb-4 flex items-center gap-2`}
            >
              <Users className={`${iconSizes.md} text-muted-foreground`} />
              面试方案
            </h3>

            <div className="space-y-2">
              {interviewCollections.map((col) => {
                const completedCount = col.rounds.filter(
                  (r) => r.status === "completed",
                ).length;
                const progress = col.rounds.length
                  ? Math.round((completedCount / col.rounds.length) * 100)
                  : 0;
                return (
                  <button
                    key={col.id}
                    type="button"
                    className="w-full rounded-lg border border-border p-3 text-left transition-all hover:bg-muted/40"
                    onClick={() => onViewInterview(col.id)}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="truncate text-xs font-medium">
                        {col.name}
                      </span>
                      <span
                        className={`shrink-0 px-2 py-0.5 rounded text-[10px] ${getStatusColor(col.status)}`}
                      >
                        {getStatusLabel(col.status)}
                      </span>
                    </div>
                    <div className="mb-1.5 h-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>
                        {completedCount}/{col.rounds.length} 轮
                      </span>
                      <span>{fmtDateTime(col.createdAt)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div className={`${card.base} p-5`}>
            <div className={emptyState.container}>
              <Users className={emptyState.icon} />
              <p className={emptyState.title}>暂无面试方案</p>
              <p className={emptyState.description}>前往面试模块创建方案</p>
            </div>
          </div>
        )}

        <div className={`${card.base} p-5`}>
          <h3
            className={`${typography.heading.md} mb-4 flex items-center gap-2`}
          >
            <Clock className={`${iconSizes.md} text-muted-foreground`} />
            分析版本
          </h3>
          {historyAnalyses.length > 0 ? (
            <div className="space-y-2">
              {historyAnalyses.slice(0, 4).map((a) => {
                const c = getScoreColorClass(a.overallScore);
                return (
                  <div
                    key={a.id}
                    className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-medium">v{a.version}</div>
                      <div className="truncate text-[10px] text-muted-foreground">
                        {fmtDateTime(a.createdAt)}
                      </div>
                    </div>
                    <span
                      className={`text-xs font-semibold tabular-nums ${c.text}`}
                    >
                      {a.overallScore}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className={typography.caption.md}>暂无历史版本</p>
          )}
        </div>
      </aside>
    </div>
  );
}
