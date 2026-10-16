import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export interface InterviewerProfile {
  name: string;
  title: string;
  bio: string;
  questionStyle: string;
  assessmentDimensions: string[];
  personalityTraits: string[];
}

interface CustomInterviewerModalProps {
  open: boolean;
  onClose: () => void;
  initialValues?: InterviewerProfile;
  isEdit?: boolean;
  onSubmit: (profile: InterviewerProfile) => void;
}

const REQUIRED_MSG = '此项为必填';

export default function CustomInterviewerModal({
  open,
  onClose,
  initialValues,
  isEdit,
  onSubmit,
}: CustomInterviewerModalProps) {
  const [name, setName] = useState('');
  const [title, setTitle] = useState('');
  const [bio, setBio] = useState('');
  const [questionStyle, setQuestionStyle] = useState('');
  const [assessmentDimensions, setAssessmentDimensions] = useState('');
  const [personalityTraits, setPersonalityTraits] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open && initialValues) {
      setName(initialValues.name);
      setTitle(initialValues.title);
      setBio(initialValues.bio);
      setQuestionStyle(initialValues.questionStyle);
      setAssessmentDimensions(initialValues.assessmentDimensions.join('，'));
      setPersonalityTraits(initialValues.personalityTraits.join('，'));
    } else if (!open) {
      setName('');
      setTitle('');
      setBio('');
      setQuestionStyle('');
      setAssessmentDimensions('');
      setPersonalityTraits('');
    }
    setErrors({});
  }, [open, initialValues]);

  if (!open) return null;

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!name.trim()) newErrors.name = REQUIRED_MSG;
    if (!title.trim()) newErrors.title = REQUIRED_MSG;
    if (!bio.trim()) newErrors.bio = REQUIRED_MSG;
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

  const handleSubmit = () => {
    if (!validate()) return;
    onSubmit({
      name: name.trim(),
      title: title.trim(),
      bio: bio.trim(),
      questionStyle: questionStyle.trim(),
      assessmentDimensions: assessmentDimensions
        .split(/[,，]/)
        .map((s) => s.trim())
        .filter(Boolean),
      personalityTraits: personalityTraits
        .split(/[,，]/)
        .map((s) => s.trim())
        .filter(Boolean),
    });
    setName('');
    setTitle('');
    setBio('');
    setQuestionStyle('');
    setAssessmentDimensions('');
    setPersonalityTraits('');
  };

  const inputCls = (fieldKey: string) =>
    `w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50 ${
      errors[fieldKey] ? 'border-red-500/60' : 'border-foreground/10'
    }`;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-xl shadow-2xl w-full max-w-md mx-4 flex flex-col max-h-[85vh]">
        <div className="flex items-center justify-between p-5 border-b border-border shrink-0">
          <h2 className="text-sm font-semibold">{isEdit ? '编辑面试官' : '自定义面试官'}</h2>
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
            <label className="text-xs text-muted-foreground mb-1.5 block">
              面试官名称 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                clearError('name');
              }}
              placeholder="如：产品总监"
              className={inputCls('name')}
              autoFocus
            />
            {errors.name && <p className="text-[10px] text-red-400 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              职位头衔 <span className="text-primary">*</span>
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                clearError('title');
              }}
              placeholder="如：产品副总裁"
              className={inputCls('title')}
            />
            {errors.title && <p className="text-[10px] text-red-400 mt-1">{errors.title}</p>}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">
              简介 <span className="text-primary">*</span>
            </label>
            <textarea
              value={bio}
              onChange={(e) => {
                setBio(e.target.value);
                clearError('bio');
              }}
              placeholder="描述面试官的背景..."
              rows={2}
              className={`${inputCls('bio')} resize-none`}
            />
            {errors.bio && <p className="text-[10px] text-red-400 mt-1">{errors.bio}</p>}
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
              placeholder="描述提问方式..."
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
              placeholder="如：产品思维, 数据分析, 用户洞察"
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
              placeholder="如：严谨、注重细节"
              className="w-full px-3 py-2 bg-background border border-foreground/10 rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500/50"
            />
          </div>
        </div>

        <div className="p-5 border-t border-border shrink-0">
          <button
            type="button"
            onClick={handleSubmit}
            className="w-full px-4 py-2 rounded-lg bg-teal-500 text-white text-sm font-medium hover:bg-teal-600 transition-colors"
          >
            {isEdit ? '保存' : '添加'}
          </button>
        </div>
      </div>
    </div>
  );
}
