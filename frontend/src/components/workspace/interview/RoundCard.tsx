import { ChevronUp, ChevronDown, Trash2, Edit3 } from 'lucide-react';
import type { InterviewerProfile } from './CustomInterviewerModal';

interface DraftRound {
  tempId: string;
  name: string;
  interviewer: InterviewerProfile;
}

interface RoundCardProps {
  round: DraftRound;
  index: number;
  totalCount: number;
  onEdit: () => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

export default function RoundCard({
  round,
  index,
  totalCount,
  onEdit,
  onDelete,
  onMoveUp,
  onMoveDown,
}: RoundCardProps) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-border bg-card hover:border-teal-500/30 transition-colors group">
      <div className="flex flex-col gap-0.5">
        <button
          type="button"
          onClick={onMoveUp}
          disabled={index === 0}
          className="p-0.5 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronUp className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={onMoveDown}
          disabled={index === totalCount - 1}
          className="p-0.5 rounded text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[10px] text-muted-foreground font-mono">#{index + 1}</span>
          <span className="text-xs font-medium truncate">{round.name}</span>
        </div>
        <p className="text-[10px] text-muted-foreground truncate">
          {round.interviewer.name}
          {round.interviewer.title && ` · ${round.interviewer.title}`}
        </p>
      </div>

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          onClick={onEdit}
          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
          title="编辑"
        >
          <Edit3 className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
          title="删除"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
