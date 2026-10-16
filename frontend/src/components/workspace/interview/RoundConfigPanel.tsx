import { useState, useEffect } from 'react';
import { X, UserPlus } from 'lucide-react';
import CustomInterviewerModal, { type InterviewerProfile } from './CustomInterviewerModal';

interface DraftRound {
  tempId: string;
  name: string;
  interviewer: InterviewerProfile;
}

interface RoundConfigPanelProps {
  open: boolean;
  onClose: () => void;
  initialData?: DraftRound;
  onSubmit: (round: DraftRound) => void;
}

function generateTempId(): string {
  return `draft_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function RoundConfigPanel({
  open,
  onClose,
  initialData,
  onSubmit,
}: RoundConfigPanelProps) {
  const [name, setName] = useState('');
  const [interviewer, setInterviewer] = useState<InterviewerProfile>({
    name: '',
    title: '',
    bio: '',
    questionStyle: '',
    assessmentDimensions: [],
    personalityTraits: [],
  });
  const [showInterviewerModal, setShowInterviewerModal] = useState(false);

  useEffect(() => {
    if (open) {
      if (initialData) {
        setName(initialData.name);
        setInterviewer(initialData.interviewer);
      } else {
        setName('');
        setInterviewer({
          name: '',
          title: '',
          bio: '',
          questionStyle: '',
          assessmentDimensions: [],
          personalityTraits: [],
        });
      }
    }
  }, [open, initialData]);

  if (!open) return null;

  const handleSubmit = () => {
    if (!name.trim() || !interviewer.name.trim()) return;
    onSubmit({
      tempId: initialData?.tempId ?? generateTempId(),
      name: name.trim(),
      interviewer: {
        name: interviewer.name.trim(),
        title: interviewer.title.trim(),
        bio: interviewer.bio.trim(),
        questionStyle: interviewer.questionStyle.trim(),
        assessmentDimensions: interviewer.assessmentDimensions,
        personalityTraits: interviewer.personalityTraits,
      },
    });
  };

  const handleInterviewerSubmit = (profile: InterviewerProfile) => {
    setInterviewer(profile);
    setShowInterviewerModal(false);
  };

  return (
    <>
      <div className="fixed inset-0 z-[55] flex items-center justify-center">
        <div className="absolute inset-0 bg-black/60" onClick={onClose} />
        <div className="relative bg-card border border-border rounded-xl p-6 w-full max-w-lg mx-4 shadow-2xl max-h-[85vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-sm font-semibold">
              {initialData ? '编辑面试轮次' : '添加面试轮次'}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-muted-foreground mb-1.5 block">
                轮次名称 <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：技术一面"
                className="w-full px-3 py-2 bg-background border border-foreground/10 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50"
                autoFocus
              />
            </div>

            <div className="border-t border-border pt-4">
              <div className="flex items-center justify-between mb-3">
                <label className="text-xs text-muted-foreground">
                  面试官信息 <span className="text-red-400">*</span>
                </label>
                <button
                  type="button"
                  onClick={() => setShowInterviewerModal(true)}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-primary hover:bg-teal-500/10 transition-colors"
                >
                  <UserPlus className="w-3 h-3" />
                  自定义面试官
                </button>
              </div>

              {interviewer.name ? (
                <div className="p-3 rounded-lg border border-border bg-background">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium">{interviewer.name}</span>
                    {interviewer.title && (
                      <span className="text-[10px] text-muted-foreground">{interviewer.title}</span>
                    )}
                  </div>
                  {interviewer.bio && (
                    <p className="text-[10px] text-muted-foreground line-clamp-1">
                      {interviewer.bio}
                    </p>
                  )}
                  {interviewer.questionStyle && (
                    <p className="text-[10px] text-muted-foreground mt-1">
                      风格：{interviewer.questionStyle}
                    </p>
                  )}
                  {interviewer.assessmentDimensions.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {interviewer.assessmentDimensions.map((dim) => (
                        <span
                          key={dim}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 text-primary"
                        >
                          {dim}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-4 rounded-lg border border-dashed border-border text-center">
                  <p className="text-xs text-muted-foreground">
                    点击「自定义面试官」配置面试官信息
                  </p>
                </div>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!name.trim() || !interviewer.name.trim()}
            className="w-full mt-6 px-4 py-2 rounded-lg bg-teal-500 text-white text-sm font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {initialData ? '保存修改' : '添加轮次'}
          </button>
        </div>
      </div>

      <CustomInterviewerModal
        open={showInterviewerModal}
        onClose={() => setShowInterviewerModal(false)}
        onSubmit={handleInterviewerSubmit}
      />
    </>
  );
}
