import { useEffect, useState } from 'react';
import { X, Plus, Pencil } from 'lucide-react';
import { fetchBuiltInInterviewers } from '@/lib/api';
import type {
  BuiltInInterviewer,
  BuiltInInterviewerType,
  InterviewRoundDraft,
} from '@/types/interview';
import CustomInterviewerModal, { type InterviewerProfile } from './CustomInterviewerModal';

interface SelectedInterviewer {
  id: string;
  name: string;
  title: string;
  roundName: string;
  avatarText: string;
  avatarColor: string;
  bio: string;
  questionStyle: string;
  assessmentDimensions: string[];
  personalityTraits: string[];
  interviewerType?: BuiltInInterviewerType;
  isBuiltIn: boolean;
}

interface CreateInterviewModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, rounds: InterviewRoundDraft[]) => Promise<void>;
}

export default function CreateInterviewModal({
  open,
  onClose,
  onSubmit,
}: CreateInterviewModalProps) {
  const [name, setName] = useState('');
  const [builtInInterviewers, setBuiltInInterviewers] = useState<BuiltInInterviewer[]>([]);
  const [customInterviewers, setCustomInterviewers] = useState<SelectedInterviewer[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [overrides, setOverrides] = useState<Record<string, Partial<SelectedInterviewer>>>({});
  const [editingInterviewer, setEditingInterviewer] = useState<SelectedInterviewer | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetchBuiltInInterviewers()
      .then((data) => setBuiltInInterviewers(data))
      .catch(() => setBuiltInInterviewers([]))
      .finally(() => setLoading(false));
  }, [open]);

  // Reset state when modal closes
  const handleClose = () => {
    setName('');
    setSelectedIds([]);
    setCustomInterviewers([]);
    setOverrides({});
    setEditingInterviewer(null);
    onClose();
  };

  const handleSelectInterviewer = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      return [...prev, id];
    });
  };

  const handleAddCustomInterviewer = (profile: InterviewerProfile) => {
    const customId = `custom-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const newInterviewer: SelectedInterviewer = {
      id: customId,
      name: profile.name,
      title: profile.title,
      roundName: `${profile.name}面试`,
      avatarText: profile.name.charAt(0),
      avatarColor: '#6366f1',
      bio: profile.bio,
      questionStyle: profile.questionStyle,
      assessmentDimensions: profile.assessmentDimensions,
      personalityTraits: profile.personalityTraits,
      isBuiltIn: false,
    };
    setCustomInterviewers((prev) => [...prev, newInterviewer]);
    setSelectedIds((prev) => [...prev, customId]);
    setShowCustomModal(false);
  };

  const handleEditInterviewer = (interviewer: SelectedInterviewer) => {
    setEditingInterviewer(interviewer);
  };

  const handleSaveEdit = (profile: InterviewerProfile) => {
    if (!editingInterviewer) return;
    if (editingInterviewer.isBuiltIn) {
      setOverrides((prev) => ({
        ...prev,
        [editingInterviewer.id]: {
          name: profile.name,
          title: profile.title,
          bio: profile.bio,
          questionStyle: profile.questionStyle,
          assessmentDimensions: profile.assessmentDimensions,
          personalityTraits: profile.personalityTraits,
          roundName: `${profile.name}面试`,
          avatarText: profile.name.charAt(0),
        },
      }));
    } else {
      setCustomInterviewers((prev) =>
        prev.map((ci) =>
          ci.id === editingInterviewer.id
            ? {
                ...ci,
                name: profile.name,
                title: profile.title,
                bio: profile.bio,
                questionStyle: profile.questionStyle,
                assessmentDimensions: profile.assessmentDimensions,
                personalityTraits: profile.personalityTraits,
                roundName: `${profile.name}面试`,
                avatarText: profile.name.charAt(0),
              }
            : ci,
        ),
      );
    }
    setEditingInterviewer(null);
  };

  const handleDeleteInterviewer = (id: string) => {
    setCustomInterviewers((prev) => prev.filter((ci) => ci.id !== id));
    setSelectedIds((prev) => prev.filter((sid) => sid !== id));
  };

  const allInterviewers: SelectedInterviewer[] = [
    ...builtInInterviewers.map((bi) => {
      const override = overrides[bi.type];
      return {
        id: bi.type,
        name: override?.name ?? bi.name,
        title: override?.title ?? bi.title,
        roundName: override?.roundName ?? bi.roundName,
        avatarText: override?.avatarText ?? bi.avatarText,
        avatarColor: bi.avatarColor,
        bio: override?.bio ?? bi.bio,
        questionStyle: override?.questionStyle ?? bi.questionStyle,
        assessmentDimensions: override?.assessmentDimensions ?? bi.assessmentDimensions,
        personalityTraits: override?.personalityTraits ?? bi.personalityTraits,
        interviewerType: bi.type,
        isBuiltIn: true,
      };
    }),
    ...customInterviewers,
  ];

  const isValid = name.trim().length > 0 && selectedIds.length > 0;

  const handleSubmit = async () => {
    if (!isValid || submitting) return;
    setSubmitting(true);
    try {
      const rounds: InterviewRoundDraft[] = selectedIds.map((id) => {
        const interviewer = allInterviewers.find((i) => i.id === id)!;
        const roundName = interviewer.isBuiltIn ? interviewer.roundName : `${interviewer.name}面试`;
        return {
          name: roundName,
          interviewerName: interviewer.name,
          interviewerTitle: interviewer.title || undefined,
          interviewerBio: interviewer.bio || undefined,
          questionStyle: interviewer.questionStyle || undefined,
          assessmentDimensions:
            interviewer.assessmentDimensions.length > 0
              ? interviewer.assessmentDimensions
              : undefined,
          personalityTraits:
            interviewer.personalityTraits.length > 0 ? interviewer.personalityTraits : undefined,
          interviewerType: interviewer.interviewerType,
        };
      });
      await onSubmit(name.trim(), rounds);
      handleClose();
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/60" onClick={handleClose} />
        <div className="relative bg-card border border-border rounded-xl w-full max-w-3xl mx-4 shadow-2xl flex flex-col h-[560px] max-h-[85vh]">
          <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
            <h2 className="text-sm font-semibold">新建面试方案</h2>
            <button
              type="button"
              onClick={handleClose}
              className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {/* Title input */}
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">
                方案名称 <span className="text-primary">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="输入面试方案名称..."
                className="w-full px-3 py-2 bg-background border border-foreground/10 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50"
                autoFocus
              />
            </div>

            {/* Interviewer selection */}
            <div>
              <label className="text-xs text-muted-foreground mb-2 block">
                选择面试官 <span className="text-primary">*</span>
                <span className="ml-1.5 text-muted-foreground/60">点击选择，再次点击取消</span>
              </label>

              {loading ? (
                <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
                  加载面试官列表...
                </div>
              ) : (
                <div className="flex gap-2.5 overflow-x-auto py-2 -mx-1 px-1 scrollbar-thin">
                  {allInterviewers.map((interviewer) => {
                    const isSelected = selectedIds.includes(interviewer.id);
                    const orderIndex = isSelected ? selectedIds.indexOf(interviewer.id) + 1 : 0;

                    return (
                      <button
                        key={interviewer.id}
                        type="button"
                        onClick={() => handleSelectInterviewer(interviewer.id)}
                        className={`group relative shrink-0 w-[90px] rounded-xl border p-2.5 flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                          isSelected
                            ? 'border-teal-500 ring-2 ring-teal-500 bg-teal-500/5'
                            : 'border-border bg-card hover:border-foreground/20 hover:bg-muted/30'
                        }`}
                      >
                        {/* Hover action buttons */}
                        {!isSelected && (
                          <div className="absolute -top-1.5 -left-1.5 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                            <span
                              role="button"
                              tabIndex={0}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEditInterviewer(interviewer);
                              }}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.stopPropagation();
                                  handleEditInterviewer(interviewer);
                                }
                              }}
                              className="w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center shadow-sm hover:bg-blue-600 transition-colors cursor-pointer"
                              title="编辑"
                            >
                              <Pencil className="w-2.5 h-2.5" />
                            </span>
                            {!interviewer.isBuiltIn && (
                              <span
                                role="button"
                                tabIndex={0}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteInterviewer(interviewer.id);
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    e.stopPropagation();
                                    handleDeleteInterviewer(interviewer.id);
                                  }
                                }}
                                className="w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center shadow-sm hover:bg-red-600 transition-colors cursor-pointer"
                                title="删除"
                              >
                                <X className="w-2.5 h-2.5" />
                              </span>
                            )}
                          </div>
                        )}
                        {/* Order badge */}
                        {isSelected && (
                          <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-teal-500 text-white text-[9px] font-bold flex items-center justify-center shadow-sm z-10">
                            {orderIndex}
                          </span>
                        )}
                        {/* Avatar */}
                        <div
                          className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${
                            isSelected ? 'opacity-80' : ''
                          }`}
                          style={{ backgroundColor: interviewer.avatarColor }}
                        >
                          {interviewer.avatarText}
                        </div>
                        {/* Name */}
                        <span
                          className={`text-[11px] font-medium leading-tight text-center line-clamp-1 w-full ${
                            isSelected ? 'text-primary' : 'text-foreground'
                          }`}
                        >
                          {interviewer.name}
                        </span>
                        {/* Title */}
                        <span
                          className={`text-[9px] leading-tight text-center line-clamp-1 w-full ${
                            isSelected ? 'text-primary/70' : 'text-muted-foreground'
                          }`}
                        >
                          {interviewer.title}
                        </span>
                      </button>
                    );
                  })}

                  {/* Add custom interviewer card */}
                  <button
                    type="button"
                    onClick={() => setShowCustomModal(true)}
                    className="shrink-0 w-[90px] rounded-xl border border-dashed border-foreground/15 p-2.5 flex flex-col items-center gap-1.5 transition-all cursor-pointer hover:border-teal-500/50 hover:bg-teal-500/5"
                  >
                    <div className="w-9 h-9 rounded-full bg-muted/30 flex items-center justify-center shrink-0">
                      <Plus className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <span className="text-[11px] text-muted-foreground leading-tight text-center w-full">
                      自定义
                    </span>
                    <span className="text-[9px] text-muted-foreground/60 leading-tight text-center w-full">
                      添加面试官
                    </span>
                  </button>
                </div>
              )}
            </div>

            {/* Selected summary */}
            {selectedIds.length > 0 && (
              <div className="px-3 py-2.5 rounded-lg bg-teal-500/5 border border-teal-500/10 min-w-0">
                <span className="text-[10px] text-primary truncate block">
                  已选择 {selectedIds.length} 位面试官
                  <span className="text-muted-foreground ml-1.5 inline">
                    · 面试顺序：
                    {selectedIds
                      .map((id) => allInterviewers.find((i) => i.id === id)?.name)
                      .filter(Boolean)
                      .join(' → ')}
                  </span>
                </span>
              </div>
            )}
          </div>

          <div className="p-5 border-t border-border shrink-0">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!isValid || submitting}
              className="w-full px-4 py-2.5 rounded-lg bg-teal-500 text-white text-sm font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? '创建中...' : '开始面试'}
            </button>
          </div>
        </div>
      </div>

      <CustomInterviewerModal
        open={showCustomModal}
        onClose={() => setShowCustomModal(false)}
        onSubmit={handleAddCustomInterviewer}
      />

      <CustomInterviewerModal
        open={editingInterviewer !== null}
        onClose={() => setEditingInterviewer(null)}
        initialValues={
          editingInterviewer
            ? {
                name: editingInterviewer.name,
                title: editingInterviewer.title,
                bio: editingInterviewer.bio,
                questionStyle: editingInterviewer.questionStyle,
                assessmentDimensions: editingInterviewer.assessmentDimensions,
                personalityTraits: editingInterviewer.personalityTraits,
              }
            : undefined
        }
        isEdit
        onSubmit={handleSaveEdit}
      />
    </>
  );
}
