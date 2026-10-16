import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { fetchBuiltInInterviewers } from '@/lib/api';
import type {
  BuiltInInterviewer,
  InterviewRound,
  CreateInterviewRoundParams,
} from '@/types/interview';

const BUILT_IN_NAMES = ['李莉', '张明', '王强', '刘芳', '陈刚', '赵总'];

interface AddRoundModalProps {
  open: boolean;
  onClose: () => void;
  interviewCollectionId: string;
  nextSortOrder: number;
  initialData?: InterviewRound | null;
  existingRounds?: InterviewRound[];
  onSubmit: (params: CreateInterviewRoundParams & { id?: string }) => Promise<void>;
}

const REQUIRED_MSG = '此项为必填';

export default function AddRoundModal({
  open,
  onClose,
  interviewCollectionId,
  nextSortOrder,
  initialData,
  existingRounds = [],
  onSubmit,
}: AddRoundModalProps) {
  const isEditMode = !!initialData;

  const [name, setName] = useState('');
  const [interviewerName, setInterviewerName] = useState('');
  const [interviewerTitle, setInterviewerTitle] = useState('');
  const [interviewerBio, setInterviewerBio] = useState('');
  const [questionStyle, setQuestionStyle] = useState('');
  const [assessmentDimensions, setAssessmentDimensions] = useState('');
  const [personalityTraits, setPersonalityTraits] = useState('');
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [builtInInterviewers, setBuiltInInterviewers] = useState<BuiltInInterviewer[]>([]);
  const [loadingBuiltIn, setLoadingBuiltIn] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoadingBuiltIn(true);
    fetchBuiltInInterviewers()
      .then((data) => setBuiltInInterviewers(data))
      .catch(() => setBuiltInInterviewers([]))
      .finally(() => setLoadingBuiltIn(false));
  }, [open]);

  useEffect(() => {
    if (open && initialData) {
      setName(initialData.name);
      setInterviewerName(initialData.interviewerName);
      setInterviewerTitle(initialData.interviewerTitle || '');
      setInterviewerBio(initialData.interviewerBio || '');
      setQuestionStyle(initialData.questionStyle || '');
      setAssessmentDimensions((initialData.assessmentDimensions || []).join(', '));
      setPersonalityTraits((initialData.personalityTraits || []).join(', '));
    } else if (open) {
      setName('');
      setInterviewerName('');
      setInterviewerTitle('');
      setInterviewerBio('');
      setQuestionStyle('');
      setAssessmentDimensions('');
      setPersonalityTraits('');
    }
    setErrors({});
  }, [open, initialData]);

  const usedNames = new Set(
    existingRounds
      .filter((r) => BUILT_IN_NAMES.includes(r.interviewerName))
      .map((r) => r.interviewerName),
  );

  const handleSelectBuiltIn = (interviewer: BuiltInInterviewer) => {
    if (usedNames.has(interviewer.name)) return;
    setName(interviewer.roundName);
    setInterviewerName(interviewer.name);
    setInterviewerTitle(interviewer.title);
    setInterviewerBio(interviewer.bio);
    setQuestionStyle(interviewer.questionStyle);
    setAssessmentDimensions(interviewer.assessmentDimensions.join(', '));
    setPersonalityTraits(interviewer.personalityTraits.join(', '));
    setErrors({});
  };

  if (!open) return null;

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = REQUIRED_MSG;
    if (!interviewerName.trim()) newErrors.interviewerName = REQUIRED_MSG;
    if (!interviewerTitle.trim()) newErrors.interviewerTitle = REQUIRED_MSG;
    if (!interviewerBio.trim()) newErrors.interviewerBio = REQUIRED_MSG;
    if (!questionStyle.trim()) newErrors.questionStyle = REQUIRED_MSG;
    if (!assessmentDimensions.trim()) newErrors.assessmentDimensions = REQUIRED_MSG;
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const clearError = (field: string) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const params: CreateInterviewRoundParams & { id?: string } = {
        interviewCollectionId,
        name: name.trim(),
        interviewerName: interviewerName.trim(),
        interviewerTitle: interviewerTitle.trim(),
        interviewerBio: interviewerBio.trim(),
        questionStyle: questionStyle.trim(),
        assessmentDimensions: assessmentDimensions
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        personalityTraits: personalityTraits
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        sortOrder: initialData ? initialData.sortOrder : nextSortOrder,
      };
      if (isEditMode && initialData) {
        params.id = initialData.id;
      }
      await onSubmit(params);
      onClose();
    } catch {
    } finally {
      setLoading(false);
    }
  };

  const inputCls = (fieldKey: string) =>
    `w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50 ${
      errors[fieldKey] ? 'border-red-500/60' : 'border-foreground/10'
    }`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg mx-4 flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-sm font-semibold">{isEditMode ? '编辑面试轮次' : '添加面试轮次'}</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-2 block">快速选择面试官</label>
            {loadingBuiltIn ? (
              <div className="text-[10px] text-muted-foreground py-2">加载中...</div>
            ) : builtInInterviewers.length > 0 ? (
              <div className="flex gap-2 overflow-x-auto py-1.5 -mx-1 px-1">
                {builtInInterviewers.map((bi) => {
                  const isUsed = usedNames.has(bi.name);
                  const isActive = interviewerName === bi.name;
                  return (
                    <button
                      key={bi.type}
                      type="button"
                      disabled={isUsed}
                      onClick={() => handleSelectBuiltIn(bi)}
                      className={`group shrink-0 w-[72px] rounded-lg border p-2 flex flex-col items-center gap-1 transition-all ${
                        isUsed
                          ? 'border-border/30 bg-muted/10 opacity-40 cursor-not-allowed'
                          : isActive
                            ? 'border-teal-500 ring-1 ring-teal-500 bg-teal-500/5 cursor-default'
                            : 'border-border bg-card hover:border-foreground/20 hover:bg-muted/30 cursor-pointer'
                      }`}
                      title={isUsed ? '该面试官已在此方案中' : `使用 ${bi.name} 的资料`}
                    >
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                        style={{
                          backgroundColor: isUsed ? '#4B5563' : bi.avatarColor,
                        }}
                      >
                        {bi.avatarText}
                      </div>
                      <span
                        className={`text-[10px] font-medium leading-tight text-center line-clamp-1 w-full ${
                          isUsed
                            ? 'text-muted-foreground'
                            : isActive
                              ? 'text-primary'
                              : 'text-foreground'
                        }`}
                      >
                        {bi.name}
                      </span>
                      <span className="text-[8px] text-muted-foreground leading-tight text-center line-clamp-1 w-full">
                        {bi.roundName}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className="border-t border-border/30" />

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              轮次名称 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                clearError('name');
              }}
              placeholder="例如：技术一面"
              className={inputCls('name')}
            />
            {errors.name && <p className="text-[10px] text-red-400 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              面试官名称 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={interviewerName}
              onChange={(e) => {
                setInterviewerName(e.target.value);
                clearError('interviewerName');
              }}
              placeholder="例如：张明"
              className={inputCls('interviewerName')}
            />
            {errors.interviewerName && (
              <p className="text-[10px] text-red-400 mt-1">{errors.interviewerName}</p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              面试官头衔 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={interviewerTitle}
              onChange={(e) => {
                setInterviewerTitle(e.target.value);
                clearError('interviewerTitle');
              }}
              placeholder="例如：技术架构师"
              className={inputCls('interviewerTitle')}
            />
            {errors.interviewerTitle && (
              <p className="text-[10px] text-red-400 mt-1">{errors.interviewerTitle}</p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              面试官简介 <span className="text-primary">*</span>
            </label>
            <textarea
              value={interviewerBio}
              onChange={(e) => {
                setInterviewerBio(e.target.value);
                clearError('interviewerBio');
              }}
              placeholder="描述面试官的背景和风格"
              rows={2}
              className={`${inputCls('interviewerBio')} resize-none`}
            />
            {errors.interviewerBio && (
              <p className="text-[10px] text-red-400 mt-1">{errors.interviewerBio}</p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              提问风格 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={questionStyle}
              onChange={(e) => {
                setQuestionStyle(e.target.value);
                clearError('questionStyle');
              }}
              placeholder="例如：由浅入深、追问细节"
              className={inputCls('questionStyle')}
            />
            {errors.questionStyle && (
              <p className="text-[10px] text-red-400 mt-1">{errors.questionStyle}</p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              考察维度（逗号分隔） <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={assessmentDimensions}
              onChange={(e) => {
                setAssessmentDimensions(e.target.value);
                clearError('assessmentDimensions');
              }}
              placeholder="例如：算法能力, 系统设计, 代码质量"
              className={inputCls('assessmentDimensions')}
            />
            {errors.assessmentDimensions && (
              <p className="text-[10px] text-red-400 mt-1">{errors.assessmentDimensions}</p>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              性格特征（逗号分隔）
            </label>
            <input
              type="text"
              value={personalityTraits}
              onChange={(e) => setPersonalityTraits(e.target.value)}
              placeholder="例如：严谨, 善于引导, 注重实践"
              className="w-full px-3 py-2 bg-background border border-foreground/10 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50"
            />
          </div>
        </div>

        <div className="p-5 border-t border-border shrink-0">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="w-full px-4 py-2 rounded-lg bg-teal-500 text-white text-sm font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading
              ? isEditMode
                ? '保存中...'
                : '添加中...'
              : isEditMode
                ? '保存修改'
                : '添加轮次'}
          </button>
        </div>
      </div>
    </div>
  );
}
