import { useState, useMemo } from "react";
import type { ReactNode } from "react";
import {
  Square,
  Lightbulb,
  Zap,
  Target,
  BarChart2,
  Award,
  GraduationCap,
  Star,
  FileText,
  Pencil,
  Key,
  Ruler,
  Building,
  Minus,
  Info,
  Check,
  TrendingUp,
  AlertCircle,
  // keep existing ones
  RefreshCw,
} from "lucide-react";
import type { JdAnalysis, JdRequirement } from "../../types/workspace";
import { getScoreColorClass, fmtDateTime } from "../../lib/resume-insights";
import { enrichJdAnalysisList } from "../../lib/jd-analysis-adapter";
import ConfirmDialog from "../ui/ConfirmDialog";
import {
  typography,
  card,
  icon as iconSizes,
} from "../../lib/component-styles";
import ScoreRing from "./ScoreRing";

interface JDAnalysisTabProps {
  analyses: JdAnalysis[];
  selectedId?: number;
  onSelectAnalysis?: (analysisId: number) => void;
  onStartScoring?: () => void;
}

type KeywordTab = "matched" | "partial" | "missing";

export default function JDAnalysisTab({
  analyses,
  selectedId: propSelectedId,
  onSelectAnalysis,
  onStartScoring,
}: JDAnalysisTabProps) {
  const enrichedList = useMemo(
    () => enrichJdAnalysisList(analyses),
    [analyses],
  );
  const effectiveSelectedId = propSelectedId ?? enrichedList[0]?.id ?? 0;
  const [activeKwTab, setActiveKwTab] = useState<KeywordTab>("matched");

  const [showConfirmScoring, setShowConfirmScoring] = useState(false);

  const record = useMemo(
    () =>
      enrichedList.find((a) => a.id === effectiveSelectedId) ||
      enrichedList[0] ||
      null,
    [enrichedList, effectiveSelectedId],
  );

  const handleSelectId = (id: number) => {
    onSelectAnalysis?.(id);
  };

  if (!record) {
    return (
      <>
        <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
          <FileText className="w-12 h-12 opacity-10" />
          <p className="text-sm">暂无 JD 分析记录</p>
          <p className="text-xs opacity-60">请先对子简历进行 JD 评分</p>
          {onStartScoring && (
            <button
              type="button"
              onClick={() => setShowConfirmScoring(true)}
              className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-xs bg-muted/70 text-foreground border border-border hover:bg-muted transition-colors"
            >
              <Star className="w-3 h-3" />
              开始评分
            </button>
          )}
        </div>
        <ConfirmDialog
          open={showConfirmScoring}
          title="确认发起 JD 评分"
          description="将根据当前子简历的 JD 描述进行 AI 匹配评分，评分过程可能需要一些时间。"
          confirmText="开始评分"
          cancelText="取消"
          onConfirm={() => {
            setShowConfirmScoring(false);
            onStartScoring?.();
          }}
          onCancel={() => setShowConfirmScoring(false)}
        />
      </>
    );
  }

  const keywordMatchesArr =
    Array.isArray(record.keywordMatches) &&
    typeof record.keywordMatches[0] === "object"
      ? (record.keywordMatches as any[])
      : [];
  const partialMatchesArr = record.partialMatches || [];
  const missingKeywordsArr =
    Array.isArray(record.missingKeywords) &&
    typeof record.missingKeywords[0] === "object"
      ? (record.missingKeywords as any[])
      : [];
  const skillMatchesArr = record.skillMatches || [];
  const strengthsArr = record.strengths || [];
  const suggestionsArr = (record.suggestions as any[]) || [];

  const catLabels: Record<string, string> = {
    required: "必需",
    preferred: "优先",
    bonus: "加分",
  };
  const typeLabels: Record<string, string> = {
    exact: "精确匹配",
    synonym: "同义匹配",
    contextual: "上下文匹配",
  };
  const typeIcons: Record<string, ReactNode> = {
    content_gap: <FileText className="w-3 h-3" />,
    wording: <Pencil className="w-3 h-3" />,
    keyword_add: <Key className="w-3 h-3" />,
    format: <Ruler className="w-3 h-3" />,
    structure: <Building className="w-3 h-3" />,
  };
  const typeNames: Record<string, string> = {
    content_gap: "内容缺失",
    wording: "措辞优化",
    keyword_add: "关键词补充",
    format: "格式优化",
    structure: "结构调整",
  };
  const dimLabels: Record<string, string> = {
    skills: "技能维度",
    experience: "经验维度",
    education: "教育维度",
  };
  const strengthIcons: Record<string, ReactNode> = {
    skill_match: <Zap className="w-3 h-3" />,
    experience_match: <Target className="w-3 h-3" />,
    project_relevance: <BarChart2 className="w-3 h-3" />,
    certification: <Award className="w-3 h-3" />,
    education_match: <GraduationCap className="w-3 h-3" />,
    unique_advantage: <Star className="w-3 h-3" />,
  };

  const reqCatLabels: Record<JdRequirement["category"], string> = {
    hard_skill: "技术栈",
    soft_skill: "软技能",
    tool: "工具/平台",
    domain_knowledge: "领域知识",
    certification: "证书/资质",
    education: "学历要求",
    experience: "工作经验",
    language: "语言能力",
  };
  const reqCatOrder: JdRequirement["category"][] = [
    "hard_skill",
    "experience",
    "education",
    "tool",
    "domain_knowledge",
    "certification",
    "soft_skill",
    "language",
  ];
  const reqImportanceLabels: Record<JdRequirement["importance"], string> = {
    mandatory: "硬性要求",
    preferred: "优先项",
    bonus: "加分项",
  };
  const reqImportanceStyles: Record<
    JdRequirement["importance"],
    { accentColor: string; bg: string; text: string }
  > = {
    mandatory: {
      accentColor: "hsl(var(--primary))",
      bg: "bg-primary/10",
      text: "text-primary",
    },
    preferred: {
      accentColor: "#fbbf24",
      bg: "bg-amber-100 dark:bg-amber-500/15",
      text: "text-amber-700 dark:text-amber-300",
    },
    bonus: {
      accentColor: "#94a3b8",
      bg: "bg-slate-100 dark:bg-slate-500/15",
      text: "text-slate-600 dark:text-slate-400",
    },
  };

  const renderImportanceDots = (importance: number, colorClass: string) => {
    return Array.from({ length: 5 }, (_, i) => (
      <span
        key={i}
        className={`inline-block w-1.5 h-1.5 rounded-full mr-0.5 ${i < importance ? colorClass : "bg-white/10"}`}
      />
    ));
  };

  const renderKeywordContent = () => {
    if (activeKwTab === "matched") {
      if (!keywordMatchesArr.length)
        return (
          <div className="text-center py-8 text-muted-foreground text-sm">
            暂无完全匹配的关键词
          </div>
        );
      return keywordMatchesArr.map((item: any, idx: number) => {
        const catClass =
          item.category === "required"
            ? "bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300 border-red-300 dark:border-red-500/30"
            : item.category === "preferred"
              ? "bg-yellow-100 dark:bg-yellow-500/15 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-500/30"
              : "bg-blue-100 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/30";
        return (
          <div
            key={idx}
            className="flex items-start gap-3 py-3 border-b border-border/50 last:border-0"
          >
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded border ${catClass}`}
              >
                {catLabels[item.category] || item.category}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium break-all">
                  {item.keyword}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-300 shrink-0">
                  {typeLabels[item.matchType] || item.matchType}
                </span>
              </div>
              <div className="flex items-center gap-1 mb-1">
                {renderImportanceDots(item.importance, "text-green-400")}
              </div>
              {item.evidence && (
                <div className="text-[10px] text-muted-foreground mt-1 break-all">
                  <span className="opacity-60">匹配证据：</span>
                  {item.evidence}
                </div>
              )}
            </div>
          </div>
        );
      });
    }
    if (activeKwTab === "partial") {
      if (!partialMatchesArr.length)
        return (
          <div className="text-center py-8 text-muted-foreground text-sm">
            暂无部分匹配项
          </div>
        );
      return partialMatchesArr.map((item: any, idx: number) => (
        <div
          key={idx}
          className="flex items-start gap-3 py-3 border-b border-border/50 last:border-0"
        >
          <div className="mt-0.5 w-5 h-5 rounded-full bg-yellow-500/10 flex items-center justify-center shrink-0">
            <Minus className="w-3 h-3 text-yellow-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium mb-1 break-all">
              {item.keyword}
            </div>
            <div className="flex items-center gap-4 text-[10px] text-muted-foreground mb-1.5 min-w-0 overflow-x-hidden">
              <span className="break-all min-w-0">
                简历：
                <span className="text-yellow-400">{item.resumeLevel}</span>
              </span>
              <span className="break-all min-w-0">
                JD 要求：
                <span className="text-foreground">{item.jobLevel}</span>
              </span>
            </div>
            <div className="text-[10px] text-muted-foreground bg-yellow-500/5 border border-yellow-500/10 rounded px-2 py-1.5 break-all">
              {item.gapDescription}
            </div>
          </div>
        </div>
      ));
    }
    if (!missingKeywordsArr.length)
      return (
        <div className="text-center py-8 text-muted-foreground text-sm">
          暂无缺失关键词
        </div>
      );
    return missingKeywordsArr.map((item: any, idx: number) => {
      const catClass =
        item.category === "required"
          ? "bg-red-100 dark:bg-red-500/15 text-red-700 dark:text-red-300 border-red-300 dark:border-red-500/30"
          : item.category === "preferred"
            ? "bg-yellow-100 dark:bg-yellow-500/15 text-yellow-700 dark:text-yellow-300 border-yellow-300 dark:border-yellow-500/30"
            : "bg-blue-100 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-500/30";
      return (
        <div
          key={idx}
          className="flex items-start gap-3 py-3 border-b border-border/50 last:border-0"
        >
          <div className="flex items-center gap-2 mt-0.5">
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded border ${catClass}`}
            >
              {catLabels[item.category] || item.category}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium mb-1 break-all">
              {item.keyword}
            </div>
            <div className="flex items-center gap-1 mb-1">
              {renderImportanceDots(item.importance, "text-red-400")}
            </div>
            {item.suggestion && (
              <div className="text-[10px] text-muted-foreground bg-red-500/5 border border-red-500/10 rounded px-2 py-1.5 break-all">
                <Lightbulb className="w-3 h-3 inline-block mr-1" />{" "}
                {item.suggestion}
              </div>
            )}
          </div>
        </div>
      );
    });
  };

  const getRecordCounts = (a: JdAnalysis) => {
    const kwMatches =
      Array.isArray(a.keywordMatches) && typeof a.keywordMatches[0] === "object"
        ? (a.keywordMatches as any[]).length
        : 0;
    const partialMatches = a.partialMatches ? a.partialMatches.length : 0;
    const missingKw =
      Array.isArray(a.missingKeywords) &&
      typeof a.missingKeywords[0] === "object"
        ? (a.missingKeywords as any[]).length
        : 0;
    return { kwMatches, partialMatches, missingKw };
  };

  return (
    <>
      <div
        className="flex gap-4 h-full overflow-hidden fade-in min-w-0"
        style={{ minHeight: 0 }}
      >
        <aside className="w-[272px] shrink-0 overflow-y-auto rounded-xl border border-border bg-card p-3">
          <div className="flex items-center justify-between mb-3 px-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground">
                分析记录
              </span>
              <span className="text-[10px] text-muted-foreground tabular-nums">
                {enrichedList.length} 个版本
              </span>
            </div>
            {onStartScoring && (
              <button
                type="button"
                onClick={() => setShowConfirmScoring(true)}
                className="flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 text-[11px] hover:bg-primary/15 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                重新评分
              </button>
            )}
          </div>
          <div className="space-y-1.5">
            {enrichedList.map((a) => {
              const sc = getScoreColorClass(a.overallScore);
              const isActive = a.id === effectiveSelectedId;
              const counts = getRecordCounts(a);
              const total =
                counts.kwMatches + counts.partialMatches + counts.missingKw;
              return (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => handleSelectId(a.id)}
                  className={`w-full text-left rounded-lg border px-3 py-3 cursor-pointer transition-all relative ${
                    isActive
                      ? "bg-primary/10 border-primary/25 shadow-sm"
                      : "border-transparent hover:bg-muted/60 hover:border-border"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={`text-lg font-semibold tabular-nums ${isActive ? "text-primary" : sc.text}`}
                    >
                      {a.overallScore}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-muted-foreground tabular-nums">
                        v{a.version}
                      </span>
                      {a.id === enrichedList[0]?.id && (
                        <span className="rounded-full bg-green-500/10 px-1.5 py-0.5 text-[9px] font-medium text-green-600 dark:text-green-400">
                          最新
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="tabular-nums">
                      {fmtDateTime(a.createdAt)}
                    </span>
                    <span className="tabular-nums">
                      {counts.kwMatches}/{total || 0} 命中
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <div
          className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden"
          style={{ height: "100%" }}
        >
          <div className="w-full max-w-full space-y-4 pr-1 pb-4">
            <div className={`${card.base} overflow-hidden`}>
              <div className="grid grid-cols-[180px_minmax(0,1fr)] gap-0">
                <div className="flex flex-col items-center justify-center border-r border-border bg-muted/30 p-5">
                  <ScoreRing
                    score={record.overallScore}
                    label="总体匹配"
                    size="lg"
                  />
                  <div className="mt-3 text-center text-[11px] text-muted-foreground">
                    v{record.version} · {fmtDateTime(record.createdAt)}
                  </div>
                </div>

                <div className="min-w-0 p-5 space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>ATS 兼容性</span>
                        <TrendingUp className="h-3.5 w-3.5" />
                      </div>
                      <div className="mt-2 flex items-end gap-1">
                        <span
                          className={`text-xl font-semibold tabular-nums ${getScoreColorClass(record.atsScore).text}`}
                        >
                          {record.atsScore}
                        </span>
                        <span className="pb-0.5 text-[10px] text-muted-foreground">
                          /100
                        </span>
                      </div>
                    </div>
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="text-[11px] text-muted-foreground">
                        完全命中
                      </div>
                      <div className="mt-2 text-xl font-semibold tabular-nums text-green-600 dark:text-green-400">
                        {keywordMatchesArr.length}
                      </div>
                    </div>
                    <div className="rounded-lg border border-border bg-background p-3">
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>缺口</span>
                        <AlertCircle className="h-3.5 w-3.5" />
                      </div>
                      <div className="mt-2 text-xl font-semibold tabular-nums text-amber-600 dark:text-amber-400">
                        {partialMatchesArr.length + missingKeywordsArr.length}
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="mb-2 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">
                        ATS 评分区间
                      </span>
                      <span className="font-medium text-foreground tabular-nums">
                        {record.atsScore}%
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 bg-gradient-to-r ${getScoreColorClass(record.atsScore).barFrom} ${getScoreColorClass(record.atsScore).barTo}`}
                        style={{ width: `${record.atsScore}%` }}
                      />
                    </div>
                    <div className="grid grid-cols-4 pt-1 text-[10px] text-muted-foreground">
                      <span className="text-left">差</span>
                      <span className="text-center">一般</span>
                      <span className="text-center">良好</span>
                      <span className="text-right">优秀</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-t border-border px-5 py-4">
                <p className="text-sm text-muted-foreground leading-relaxed break-all">
                  {record.summary}
                </p>
              </div>
              {strengthsArr.length > 0 && (
                <div className="flex flex-wrap gap-1.5 border-t border-border px-5 py-3 overflow-x-hidden">
                  {strengthsArr.slice(0, 6).map((s: any, idx: number) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-500/30 whitespace-nowrap max-w-full overflow-hidden text-ellipsis min-w-0"
                    >
                      {strengthIcons[s.type] || <Check className="w-3 h-3" />}{" "}
                      {s.description}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className={`${card.base} p-5`}>
              <div className="flex items-center justify-between mb-3 min-w-0 overflow-x-hidden">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText
                    className={`${iconSizes.md} text-muted-foreground shrink-0`}
                  />
                  <h2 className={`${typography.heading.md} break-all min-w-0`}>
                    职位描述 (JD)
                  </h2>
                </div>
                <span
                  className={`${typography.caption.xs} px-2 py-0.5 rounded bg-muted shrink-0`}
                >
                  原文
                </span>
              </div>
              <p
                className={`${typography.body.md} text-muted-foreground leading-relaxed whitespace-pre-wrap break-all`}
              >
                {record.jobDescription}
              </p>
              {Array.isArray(record.jdRequirements) &&
                record.jdRequirements.length > 0 &&
                (() => {
                  const reqs = record.jdRequirements as JdRequirement[];
                  const grouped = reqCatOrder
                    .map((cat) => ({
                      cat,
                      items: reqs.filter((r) => r.category === cat),
                    }))
                    .filter((g) => g.items.length > 0);
                  return (
                    <>
                      <div className="border-t border-border my-4" />
                      <div className="flex items-center justify-between mb-3 min-w-0 overflow-x-hidden">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="w-2.5 h-2.5 rounded-full bg-primary shrink-0" />
                          <h3 className="text-sm font-semibold">JD 要求清单</h3>
                        </div>
                        <span className="text-[10px] text-muted-foreground px-2 py-0.5 rounded bg-muted shrink-0">
                          {reqs.length} 项
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mb-3 text-[10px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Square className="w-2.5 h-2.5 text-primary" />{" "}
                          硬性要求
                        </span>
                        <span className="flex items-center gap-1">
                          <Square className="w-2.5 h-2.5 text-amber-400" />{" "}
                          优先项
                        </span>
                        <span className="flex items-center gap-1">
                          <Square className="w-2.5 h-2.5 text-slate-400" />{" "}
                          加分项
                        </span>
                      </div>
                      <div className="space-y-3">
                        {grouped.map(({ cat, items }) => (
                          <div key={cat}>
                            <div className="text-[10px] text-muted-foreground mb-1.5">
                              {reqCatLabels[cat]}
                              <span className="opacity-50 ml-1">
                                ({items.length})
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {items.map((req, i) => {
                                const style =
                                  reqImportanceStyles[req.importance];
                                return (
                                  <div
                                    key={`${cat}-${i}`}
                                    className={`group relative rounded-lg ${style.bg} px-2 py-1 transition-colors hover:brightness-125`}
                                    style={{
                                      borderLeft: `3px solid ${style.accentColor}`,
                                    }}
                                    title={reqImportanceLabels[req.importance]}
                                  >
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-[11px] text-foreground leading-tight break-all">
                                        {req.name}
                                      </span>
                                      {req.level && (
                                        <span
                                          className={`text-[9px] ${style.text} opacity-80`}
                                        >
                                          {req.level}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  );
                })()}
            </div>

            {skillMatchesArr.length > 0 && (
              <div className={`${card.base} p-5`}>
                <h2 className={`${typography.heading.md} mb-4`}>
                  关键技能匹配度
                </h2>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-x-8 gap-y-3">
                  {skillMatchesArr.map((s: any, idx: number) => {
                    const sc = getScoreColorClass(s.matchScore);
                    const skCatLabels: Record<string, string> = {
                      technical: "技术栈",
                      domain: "领域知识",
                      tool: "工具",
                      soft_skill: "软技能",
                      certification: "证书",
                    };
                    return (
                      <div key={idx} className="min-w-0">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-xs break-all">{s.skill}</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                              {skCatLabels[s.category] || s.category}
                            </span>
                          </div>
                          <span className={`text-xs font-bold ${sc.text}`}>
                            {s.matchScore}%
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className={`h-full bg-gradient-to-r ${sc.barFrom} ${sc.barTo} rounded-full transition-all duration-700`}
                            style={{ width: `${s.matchScore}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className={`${card.base} overflow-hidden`}>
              <div className="flex border-b border-border px-5 min-w-0 overflow-x-hidden">
                <button
                  onClick={() => setActiveKwTab("matched")}
                  className={`py-3 px-4 text-xs font-medium flex items-center gap-1.5 transition-colors ${activeKwTab === "matched" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-green-400" />
                  完全匹配{" "}
                  <span className="text-muted-foreground font-normal">
                    ({keywordMatchesArr.length})
                  </span>
                </button>
                <button
                  onClick={() => setActiveKwTab("partial")}
                  className={`py-3 px-4 text-xs font-medium flex items-center gap-1.5 transition-colors ${activeKwTab === "partial" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
                  部分匹配{" "}
                  <span className="text-muted-foreground font-normal">
                    ({partialMatchesArr.length})
                  </span>
                </button>
                <button
                  onClick={() => setActiveKwTab("missing")}
                  className={`py-3 px-4 text-xs font-medium flex items-center gap-1.5 transition-colors ${activeKwTab === "missing" ? "text-primary" : "text-muted-foreground hover:text-foreground"}`}
                >
                  <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
                  缺失{" "}
                  <span className="text-muted-foreground font-normal">
                    ({missingKeywordsArr.length})
                  </span>
                </button>
              </div>
              <div className="p-5">{renderKeywordContent()}</div>
            </div>

            {suggestionsArr.length > 0 && (
              <div className={`${card.base} p-5`}>
                <div className="flex items-center justify-between mb-4 min-w-0 overflow-x-hidden">
                  <h2 className={`${typography.heading.md} shrink-0`}>
                    改进建议
                  </h2>
                  <div className="flex items-center gap-3 text-[10px] shrink-0">
                    <span className="flex items-center gap-1">
                      <Square className="w-2.5 h-2.5 text-red-500" /> 高优先级
                    </span>
                    <span className="flex items-center gap-1">
                      <Square className="w-2.5 h-2.5 text-yellow-500" />{" "}
                      中优先级
                    </span>
                    <span className="flex items-center gap-1">
                      <Square className="w-2.5 h-2.5 text-green-500" /> 低优先级
                    </span>
                  </div>
                </div>
                <div className="space-y-3">
                  {[...suggestionsArr]
                    .sort((a: any, b: any) => {
                      const p = { high: 3, medium: 2, low: 1 };
                      return (
                        (p[b.priority as keyof typeof p] || 0) -
                        (p[a.priority as keyof typeof p] || 0)
                      );
                    })
                    .map((s: any, idx: number) => (
                      <div
                        key={idx}
                        className="rounded-lg border border-border bg-background overflow-hidden"
                        style={{
                          borderLeft: `3px solid ${s.priority === "high" ? "#ef4444" : s.priority === "medium" ? "#facc15" : "#22c55e"}`,
                        }}
                      >
                        <div className="p-4">
                          <div className="flex items-center gap-2 mb-3 min-w-0 overflow-x-hidden">
                            <span className="text-sm shrink-0">
                              {typeIcons[s.type] || (
                                <Lightbulb className="w-3 h-3" />
                              )}
                            </span>
                            <span className="text-xs font-medium shrink-0">
                              {typeNames[s.type] || s.type}
                            </span>
                            <span
                              className={`text-[9px] px-1.5 py-0.5 rounded shrink-0 ${
                                s.priority === "high"
                                  ? "bg-red-500/10 text-red-400"
                                  : s.priority === "medium"
                                    ? "bg-yellow-500/10 text-yellow-400"
                                    : "bg-green-100 dark:bg-green-500/15 text-green-700 dark:text-green-300"
                              }`}
                            >
                              {s.priority === "high"
                                ? "高优先级"
                                : s.priority === "medium"
                                  ? "中优先级"
                                  : "低优先级"}
                            </span>
                            {s.targetDimension && (
                              <span className="text-[9px] text-muted-foreground break-all min-w-0">
                                影响：
                                {dimLabels[s.targetDimension] ||
                                  s.targetDimension}
                              </span>
                            )}
                            {s.expectedScoreDelta && (
                              <span className="text-[9px] text-green-400 ml-auto shrink-0">
                                预计 +{s.expectedScoreDelta} 分
                              </span>
                            )}
                          </div>
                          <div className="rounded-lg overflow-hidden border border-border text-sm mb-3">
                            <div
                              className="px-3 py-2 border-b border-border/50"
                              style={{ background: "rgba(239, 68, 68, 0.05)" }}
                            >
                              <div className="text-[10px] text-red-400/60 mb-1">
                                当前
                              </div>
                              <p className="text-sm text-red-400/70 line-through break-all">
                                {s.current}
                              </p>
                            </div>
                            <div
                              className="px-3 py-2"
                              style={{ background: "rgba(34, 197, 94, 0.05)" }}
                            >
                              <div className="text-[10px] text-green-400/60 mb-1">
                                建议
                              </div>
                              <p className="text-sm text-green-400 break-all">
                                {s.suggested}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-start gap-2 text-[11px] text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
                            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-muted-foreground" />
                            <span className="break-all">{s.rationale}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      <ConfirmDialog
        open={showConfirmScoring}
        title="确认发起 JD 评分"
        description="将根据当前子简历的 JD 描述进行 AI 匹配评分，评分过程可能需要一些时间。"
        confirmText="开始评分"
        cancelText="取消"
        onConfirm={() => {
          setShowConfirmScoring(false);
          onStartScoring?.();
        }}
        onCancel={() => setShowConfirmScoring(false)}
      />
    </>
  );
}
