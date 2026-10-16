import { useEffect, useState, useCallback } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Plus,
  Play,
  ChevronDown,
  ChevronRight,
  Pencil,
  Brain,
  Loader2,
  FileText,
  X,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { useNavigate, useParams } from "react-router-dom";
import { useInterviewStore } from "@/stores/interview-store";
import type {
  InterviewCollectionDetail,
  InterviewRound,
  InterviewRoundDraft,
  UpdateInterviewRoundParams,
} from "@/types/interview";
import {
  getProviderConfig,
  regenerateCollectionSummary,
  checkRunningCollectionSummaryTask,
} from "@/lib/api";
import { addNotificationTask, markUnread } from "@/lib/notification";
import type { ProviderConfig } from "@/lib/api";
import CreateInterviewModal from "./interview/CreateInterviewModal";
import AddRoundModal from "./interview/AddRoundModal";
import { Timeline, TimelineItem } from "@/components/ui/Timeline";
import { getScoreColorClass } from "../../lib/resume-insights";
import ScoreRing from "./ScoreRing";

interface InterviewTabProps {
  subResumeId: string;
  subResumeTitle?: string;
  selectedCollectionId?: string;
  onSelectCollection?: (collectionId: string) => void;
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed:
      "text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-500/15 border border-green-300 dark:border-green-500/30",
    in_progress: "text-blue-400 bg-blue-500/10 border border-blue-500/20",
    not_started: "text-muted-foreground bg-muted/30 border border-border",
  };
  return colors[status] || colors.not_started;
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: "已完成",
    in_progress: "进行中",
    not_started: "待开始",
  };
  return labels[status] || status;
}

function getRecommendationLabel(recommendation: string): string {
  const labels: Record<string, string> = {
    strong_hire: "强烈推荐",
    hire: "推荐录用",
    neutral: "中立",
    no_hire: "不推荐",
    strong_no_hire: "强烈不推荐",
  };
  return labels[recommendation] || recommendation;
}

function getRecommendationClass(recommendation: string): string {
  if (recommendation === "strong_hire" || recommendation === "hire") {
    return "text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-500/15 border-green-300 dark:border-green-500/30";
  }
  if (recommendation === "neutral") {
    return "text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-500/15 border-amber-300 dark:border-amber-500/30";
  }
  return "text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-500/15 border-red-300 dark:border-red-500/30";
}

function RoundStatusIcon({ status }: { status: string }) {
  if (status === "completed") {
    return <CheckCircle2 className="w-3 h-3 text-green-500" strokeWidth={3} />;
  }
  if (status === "in_progress") {
    return (
      <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-card" />
    );
  }
  return <Circle className="w-3 h-3 text-border" strokeWidth={3} />;
}

interface CollectionSummaryData {
  overall_score: number;
  overall_assessment: string;
  round_summaries: Array<{
    round_id: string;
    round_name: string;
    interviewer_name: string;
    interviewer_title: string;
    score: number;
    key_points: string[];
  }>;
  key_strengths: string[];
  key_weaknesses: string[];
  dimension_breakdown: Array<{
    dimension: string;
    score: number;
    comment: string;
  }>;
  recommendation: string;
  risk_flags: string[];
  generated_at: string;
}

function CollectionCard({
  collection,
  workspaceId,
  subResumeId,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
}: {
  collection: InterviewCollectionDetail;
  workspaceId: string;
  subResumeId: string;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: (collectionId: string) => void;
  onToggleExpand: (collectionId: string) => void;
}) {
  const navigate = useNavigate();
  const createRound = useInterviewStore((s) => s.createRound);
  const updateRound = useInterviewStore((s) => s.updateRound);

  const [showAddRound, setShowAddRound] = useState(false);
  const [editingRound, setEditingRound] = useState<InterviewRound | null>(null);
  const [isGeneratingCollectionSummary, setIsGeneratingCollectionSummary] =
    useState(false);
  const [collectionSummaryTaskId, setCollectionSummaryTaskId] = useState<
    string | null
  >(null);
  const [showCollectionSummaryModal, setShowCollectionSummaryModal] =
    useState(false);
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(
    null,
  );

  useEffect(() => {
    getProviderConfig()
      .then(setProviderConfig)
      .catch(() => {});
  }, []);

  const collectionSummary = (
    collection.metaInfo as Record<string, unknown> | undefined
  )?.collection_summary as CollectionSummaryData | undefined;

  const handleGenerateCollectionSummary = async () => {
    if (!providerConfig) return;

    const existing = await checkRunningCollectionSummaryTask(collection.id);
    if (existing) {
      setCollectionSummaryTaskId(existing.taskId);
      toast.error("该集合已有正在进行的总结生成任务");
      return;
    }

    setIsGeneratingCollectionSummary(true);
    try {
      const active = providerConfig.active;
      const cfg = providerConfig.providers[active];
      const { taskId } = await regenerateCollectionSummary({
        collectionId: collection.id,
        type: active,
        apiKey: cfg.apiKey,
        baseUrl: cfg.baseUrl,
        model: cfg.model,
      });

      markUnread();
      addNotificationTask({
        id: taskId,
        taskType: "collection_summary",
        status: "running",
        metaInfo: {
          title: collection.name || "",
          fileName: collection.id,
        },
        errorMessage: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });

      setCollectionSummaryTaskId(taskId);
      toast.success("集合总结生成已开始");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "生成集合总结失败");
    } finally {
      setIsGeneratingCollectionSummary(false);
    }
  };

  const sortedRounds = [...collection.rounds].sort(
    (a, b) => a.sortOrder - b.sortOrder,
  );
  const completedCount = sortedRounds.filter(
    (r) => r.status === "completed",
  ).length;
  const progressPercent =
    sortedRounds.length > 0 ? (completedCount / sortedRounds.length) * 100 : 0;

  const canStartRound = (round: InterviewRound, index: number): boolean => {
    if (round.status !== "not_started") return false;
    for (let i = 0; i < index; i++) {
      if (sortedRounds[i].status !== "completed") return false;
    }
    const hasInProgress = sortedRounds.some((r) => r.status === "in_progress");
    return !hasInProgress;
  };

  const handleStartRound = (e: React.MouseEvent, round: InterviewRound) => {
    e.stopPropagation();
    navigate(
      `/workspace/${workspaceId}/resumes/${subResumeId}/interview/${collection.id}/${round.id}`,
    );
  };

  const handleEnterInterview = (e: React.MouseEvent, round: InterviewRound) => {
    e.stopPropagation();
    navigate(
      `/workspace/${workspaceId}/resumes/${subResumeId}/interview/${collection.id}/${round.id}`,
    );
  };

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleExpand(collection.id);
  };

  const handleHeaderClick = () => {
    onSelect(collection.id);
  };

  const nextSortOrder =
    sortedRounds.length > 0
      ? Math.max(...sortedRounds.map((r) => r.sortOrder)) + 1
      : 0;

  const canAddRound = collection.status !== "completed";

  return (
    <div
      className={`rounded-xl border bg-card overflow-hidden transition-all ${
        isSelected
          ? "border-primary/30 shadow-sm"
          : "border-border hover:border-foreground/20 hover:bg-muted/30"
      }`}
    >
      <div
        onClick={handleHeaderClick}
        className={`p-4 cursor-pointer bg-card ${isExpanded ? "border-b border-border" : ""}`}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-2 min-w-0">
            <button
              type="button"
              onClick={handleToggleExpand}
              className="mt-0.5 p-0.5 rounded hover:bg-muted transition-colors text-muted-foreground"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </button>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold truncate">
                {collection.name}
              </h3>
              <p className="mt-0.5 text-[11px] text-muted-foreground">
                {completedCount}/{sortedRounds.length} 轮完成
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={`px-2 py-1 rounded-md text-[10px] ${getStatusColor(collection.status)}`}
            >
              {getStatusLabel(collection.status)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground shrink-0">
            {Math.round(progressPercent)}%
          </span>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4">
          {sortedRounds.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8 rounded-lg border border-dashed border-border bg-muted/20">
              暂无面试轮次
            </p>
          ) : (
            <Timeline>
              {sortedRounds.map((round, index) => (
                <TimelineItem
                  key={round.id}
                  icon={<RoundStatusIcon status={round.status} />}
                >
                  <div
                    className={`rounded-lg border p-3 transition-colors ${
                      round.status === "in_progress"
                        ? "border-primary/30 bg-primary/5"
                        : round.status === "completed"
                          ? "border-green-500/20 bg-green-500/5"
                          : "border-border bg-background"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <div className="min-w-0">
                        <span className="text-xs font-medium text-foreground">
                          {round.name}
                        </span>
                        {round.interviewerTitle && (
                          <span className="block text-[10px] text-muted-foreground mt-0.5">
                            {round.interviewerName} · {round.interviewerTitle}
                          </span>
                        )}
                        {!round.interviewerTitle && round.interviewerName && (
                          <span className="block text-[10px] text-muted-foreground mt-0.5">
                            {round.interviewerName}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        {round.status === "not_started" && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingRound(round);
                            }}
                            className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            title="编辑轮次"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                        )}
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded ${getStatusColor(round.status)}`}
                        >
                          {getStatusLabel(round.status)}
                        </span>
                      </div>
                    </div>

                    {round.interviewerBio && (
                      <div className="text-[10px] text-muted-foreground mb-1 line-clamp-1">
                        {round.interviewerBio}
                      </div>
                    )}

                    <div className="flex items-center gap-2 mt-3">
                      {canStartRound(round, index) && (
                        <button
                          type="button"
                          onClick={(e) => handleStartRound(e, round)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                          <Play className="w-2.5 h-2.5" />
                          开始面试
                        </button>
                      )}
                      {round.status === "completed" && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(
                              `/workspace/${workspaceId}/resumes/${subResumeId}/interview/${collection.id}/${round.id}`,
                            );
                          }}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] bg-muted/50 border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        >
                          查看详情
                        </button>
                      )}
                      {round.status === "in_progress" && (
                        <button
                          type="button"
                          onClick={(e) => handleEnterInterview(e, round)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[10px] bg-blue-100 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-500/30 hover:bg-blue-200 dark:hover:bg-blue-500/25 transition-colors"
                        >
                          <Play className="w-2.5 h-2.5" />
                          进入面试
                        </button>
                      )}
                    </div>
                  </div>
                </TimelineItem>
              ))}
            </Timeline>
          )}

          {canAddRound && (
            <button
              type="button"
              onClick={() => setShowAddRound(true)}
              className="mt-3 flex items-center gap-1.5 px-2.5 py-2 rounded-lg border border-dashed border-border text-[11px] bg-muted/30 text-foreground hover:bg-muted hover:border-foreground/20 transition-colors w-full justify-center"
            >
              <Plus className="w-3 h-3" />
              添加轮次
            </button>
          )}

          {collection.status === "completed" && (
            <div className="mt-4 pt-4 border-t border-border">
              {collectionSummary ? (
                <button
                  type="button"
                  onClick={() => setShowCollectionSummaryModal(true)}
                  className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border text-[11px] bg-muted/70 text-foreground hover:bg-muted transition-colors"
                >
                  <FileText className="w-3 h-3" />
                  查看集合总结
                </button>
              ) : collectionSummaryTaskId ? (
                <div className="flex flex-col items-center justify-center gap-2 py-4">
                  <Loader2 className="w-4 h-4 text-primary animate-spin" />
                  <span className="text-[10px] text-muted-foreground">
                    集合总结生成中...
                  </span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleGenerateCollectionSummary}
                  disabled={isGeneratingCollectionSummary}
                  className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg border border-border text-[11px] bg-muted/70 text-foreground hover:bg-muted transition-colors disabled:opacity-50"
                >
                  {isGeneratingCollectionSummary ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Brain className="w-3.5 h-3.5" />
                  )}
                  {isGeneratingCollectionSummary ? "创建中..." : "生成集合总结"}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      <AddRoundModal
        open={showAddRound}
        onClose={() => setShowAddRound(false)}
        interviewCollectionId={collection.id}
        nextSortOrder={nextSortOrder}
        existingRounds={collection.rounds}
        onSubmit={async (params) => {
          await createRound(params);
          toast.success("轮次添加成功");
        }}
      />

      <AddRoundModal
        open={!!editingRound}
        onClose={() => setEditingRound(null)}
        interviewCollectionId={collection.id}
        nextSortOrder={nextSortOrder}
        initialData={editingRound}
        existingRounds={collection.rounds}
        onSubmit={async (params) => {
          if (params.id) {
            const updateData: UpdateInterviewRoundParams = {
              id: params.id,
              name: params.name,
              interviewerName: params.interviewerName,
              interviewerTitle: params.interviewerTitle,
              interviewerBio: params.interviewerBio,
              questionStyle: params.questionStyle,
              assessmentDimensions: params.assessmentDimensions,
              personalityTraits: params.personalityTraits,
              sortOrder: params.sortOrder,
            };
            await updateRound(updateData);
            toast.success("轮次更新成功");
            setEditingRound(null);
          }
        }}
      />

      {showCollectionSummaryModal && collectionSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowCollectionSummaryModal(false)}
          />
          <div className="relative w-full max-w-5xl max-h-[90vh] bg-card border border-border rounded-xl overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
              <div>
                <h2 className="text-sm font-semibold">{collection.name}</h2>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  总体面试结果
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowCollectionSummaryModal(false)}
                className="p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="overflow-y-auto max-h-[calc(90vh-57px)] p-5 space-y-4">
              <div className="rounded-xl border border-border bg-background overflow-hidden">
                <div className="grid grid-cols-[160px_minmax(0,1fr)_180px]">
                  <div className="flex items-center justify-center border-r border-border bg-muted/30 p-5">
                    <ScoreRing
                      score={collectionSummary.overall_score}
                      label="综合评分"
                      size="lg"
                    />
                  </div>
                  <div className="min-w-0 p-5">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="text-xs font-medium text-muted-foreground">
                        录用建议
                      </span>
                      <span
                        className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${getRecommendationClass(
                          collectionSummary.recommendation,
                        )}`}
                      >
                        {getRecommendationLabel(
                          collectionSummary.recommendation,
                        )}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed text-foreground">
                      {collectionSummary.overall_assessment}
                    </p>
                  </div>
                  <div className="grid border-l border-border bg-muted/20">
                    <div className="border-b border-border p-4">
                      <div className="text-[10px] text-muted-foreground">
                        面试轮次
                      </div>
                      <div className="mt-1 text-lg font-semibold tabular-nums">
                        {collectionSummary.round_summaries.length}
                      </div>
                    </div>
                    <div className="p-4">
                      <div className="text-[10px] text-muted-foreground">
                        生成时间
                      </div>
                      <div className="mt-1 text-xs text-foreground">
                        {new Date(
                          collectionSummary.generated_at,
                        ).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {collectionSummary.key_strengths.length > 0 && (
                  <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                      <span className="text-xs font-semibold text-green-700 dark:text-green-300">
                        核心优势
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {collectionSummary.key_strengths.map((s, i) => (
                        <li
                          key={i}
                          className="flex gap-2 text-xs leading-relaxed text-muted-foreground"
                        >
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-green-500" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {collectionSummary.key_weaknesses.length > 0 && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                    <div className="mb-3 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">
                        核心短板
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {collectionSummary.key_weaknesses.map((w, i) => (
                        <li
                          key={i}
                          className="flex gap-2 text-xs leading-relaxed text-muted-foreground"
                        >
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-500" />
                          <span>{w}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {collectionSummary.dimension_breakdown.length > 0 && (
                <div className="rounded-xl border border-border bg-background p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">
                      能力维度评分
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {collectionSummary.dimension_breakdown.length} 个维度
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {collectionSummary.dimension_breakdown.map((d, i) => {
                      const dc = getScoreColorClass(d.score);
                      return (
                        <div
                          key={i}
                          className="rounded-lg border border-border p-3"
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <span className="truncate text-xs font-medium">
                              {d.dimension}
                            </span>
                            <span
                              className={`text-xs font-semibold tabular-nums ${dc.text}`}
                            >
                              {d.score}
                            </span>
                          </div>
                          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                            <div
                              className={`h-full rounded-full transition-all bg-gradient-to-r ${dc.barFrom} ${dc.barTo}`}
                              style={{ width: `${d.score}%` }}
                            />
                          </div>
                          {d.comment && (
                            <p className="mt-2 line-clamp-2 text-[10px] leading-relaxed text-muted-foreground">
                              {d.comment}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {collectionSummary.risk_flags.length > 0 && (
                <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="text-xs font-semibold text-red-700 dark:text-red-300">
                      风险提示
                    </span>
                  </div>
                  <ul className="space-y-2">
                    {collectionSummary.risk_flags.map((r, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground"
                      >
                        <span className="w-1 h-1 rounded-full bg-red-500 mt-1.5 shrink-0" />
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {collectionSummary.round_summaries.length > 0 && (
                <div className="rounded-xl border border-border bg-background p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">
                      各轮次摘要
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      按面试轮次汇总
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {collectionSummary.round_summaries.map((rs, i) => (
                      <div
                        key={i}
                        className="rounded-lg border border-border bg-card p-3"
                      >
                        <div className="mb-2 flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <span className="block truncate text-xs font-medium">
                              {rs.round_name}
                            </span>
                            <span className="mt-0.5 block truncate text-[10px] text-muted-foreground">
                              {rs.interviewer_name}
                              {rs.interviewer_title
                                ? ` · ${rs.interviewer_title}`
                                : ""}
                            </span>
                          </div>
                          <span
                            className={`shrink-0 text-sm font-semibold tabular-nums ${getScoreColorClass(rs.score).text}`}
                          >
                            {rs.score}
                          </span>
                        </div>
                        {rs.key_points.length > 0 && (
                          <ul className="space-y-1">
                            {rs.key_points.map((p, j) => (
                              <li
                                key={j}
                                className="flex gap-1.5 text-[10px] leading-relaxed text-muted-foreground"
                              >
                                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" />
                                <span>{p}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function InterviewTab({
  subResumeId,
  selectedCollectionId,
  onSelectCollection,
}: InterviewTabProps) {
  const { id: workspaceId } = useParams<{ id: string }>();
  const collections = useInterviewStore((s) => s.collections);
  const loading = useInterviewStore((s) => s.loading);
  const error = useInterviewStore((s) => s.error);
  const fetchCollections = useInterviewStore((s) => s.fetchCollections);
  const createCollectionWithRounds = useInterviewStore(
    (s) => s.createCollectionWithRounds,
  );
  const clearError = useInterviewStore((s) => s.clearError);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(new Set());

  const handleToggleExpand = useCallback((collectionId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(collectionId)) {
        next.delete(collectionId);
      } else {
        next.add(collectionId);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    fetchCollections(subResumeId);
  }, [subResumeId, fetchCollections]);

  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  if (loading && collections.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        加载中...
      </div>
    );
  }

  // 统计数据
  const totalCollections = collections.length;
  const completedCollections = collections.filter(
    (c) => c.status === "completed",
  ).length;
  const totalRounds = collections.reduce((sum, c) => sum + c.rounds.length, 0);
  const completedRounds = collections.reduce(
    (sum, c) => sum + c.rounds.filter((r) => r.status === "completed").length,
    0,
  );

  // 获取选中的方案
  const selectedCollection = selectedCollectionId
    ? collections.find((c) => c.id === selectedCollectionId)
    : collections[0];

  return (
    <div
      className="flex gap-4 h-full overflow-hidden fade-in min-w-0"
      style={{ minHeight: 0 }}
    >
      <aside className="w-[272px] shrink-0 overflow-y-auto rounded-xl border border-border bg-card p-3">
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-foreground">
              面试方案
            </span>
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {totalCollections} 个
            </span>
          </div>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 text-[11px] hover:bg-primary/15 transition-colors"
          >
            <Plus className="w-3 h-3" />
            新建
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-3">
          <div className="rounded-lg border border-border bg-background px-2.5 py-2">
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              已完成
            </div>
            <div className="mt-1 text-sm font-semibold tabular-nums">
              {completedCollections}/{totalCollections}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-background px-2.5 py-2">
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <Circle className="w-3 h-3" />
              轮次
            </div>
            <div className="mt-1 text-sm font-semibold tabular-nums">
              {completedRounds}/{totalRounds}
            </div>
          </div>
        </div>

        {collections.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
            <Users className="w-8 h-8 opacity-10" />
            <p className="text-xs">暂无面试方案</p>
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="mt-1 px-3 py-1.5 rounded-md bg-muted/70 text-foreground border border-border text-xs hover:bg-muted transition-colors"
            >
              创建方案
            </button>
          </div>
        ) : (
          <div className="space-y-1.5">
            {collections.map((collection) => {
              const isActive =
                collection.id === (selectedCollectionId || collections[0]?.id);
              const completedCount = collection.rounds.filter(
                (r) => r.status === "completed",
              ).length;
              const progress = collection.rounds.length
                ? Math.round((completedCount / collection.rounds.length) * 100)
                : 0;
              return (
                <button
                  key={collection.id}
                  type="button"
                  onClick={() => onSelectCollection?.(collection.id)}
                  className={`w-full text-left rounded-lg border px-3 py-3 cursor-pointer transition-all relative ${
                    isActive
                      ? "bg-primary/10 border-primary/25 shadow-sm"
                      : "border-transparent hover:bg-muted/60 hover:border-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className="text-xs font-medium truncate text-foreground">
                      {collection.name}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] shrink-0 ${getStatusColor(collection.status)}`}
                    >
                      {getStatusLabel(collection.status)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      {completedCount}/{collection.rounds.length}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </aside>

      {/* 右栏：选中方案的详细内容 */}
      <div
        className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden"
        style={{ height: "100%" }}
      >
        {selectedCollection ? (
          <CollectionCard
            key={selectedCollection.id}
            collection={selectedCollection}
            workspaceId={workspaceId || ""}
            subResumeId={subResumeId}
            isSelected={true}
            isExpanded={!collapsedIds.has(selectedCollection.id)}
            onSelect={(id) => onSelectCollection?.(id)}
            onToggleExpand={handleToggleExpand}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
            <Users className="w-10 h-10 opacity-10" />
            <p className="text-xs">请从左侧选择一个面试方案</p>
          </div>
        )}
      </div>

      <CreateInterviewModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={async (name, rounds: InterviewRoundDraft[]) => {
          await createCollectionWithRounds({
            name,
            subResumeId,
            rounds,
          });
          toast.success("面试方案创建成功");
        }}
      />
    </div>
  );
}
