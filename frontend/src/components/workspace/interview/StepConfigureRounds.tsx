import { useState } from 'react';
import { Plus } from 'lucide-react';
import RoundCard from './RoundCard';
import RoundConfigPanel from './RoundConfigPanel';
import type { InterviewerProfile } from './CustomInterviewerModal';

interface DraftRound {
  tempId: string;
  name: string;
  interviewer: InterviewerProfile;
}

interface StepConfigureRoundsProps {
  rounds: DraftRound[];
  onChange: (rounds: DraftRound[]) => void;
}

export default function StepConfigureRounds({ rounds, onChange }: StepConfigureRoundsProps) {
  const [configOpen, setConfigOpen] = useState(false);
  const [editingRound, setEditingRound] = useState<DraftRound | undefined>();

  const handleAddRound = (round: DraftRound) => {
    onChange([...rounds, round]);
    setConfigOpen(false);
    setEditingRound(undefined);
  };

  const handleEditRound = (round: DraftRound) => {
    onChange(rounds.map((r) => (r.tempId === round.tempId ? round : r)));
    setConfigOpen(false);
    setEditingRound(undefined);
  };

  const handleDeleteRound = (tempId: string) => {
    onChange(rounds.filter((r) => r.tempId !== tempId));
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newRounds = [...rounds];
    [newRounds[index - 1], newRounds[index]] = [newRounds[index], newRounds[index - 1]];
    onChange(newRounds);
  };

  const handleMoveDown = (index: number) => {
    if (index === rounds.length - 1) return;
    const newRounds = [...rounds];
    [newRounds[index], newRounds[index + 1]] = [newRounds[index + 1], newRounds[index]];
    onChange(newRounds);
  };

  const openAddPanel = () => {
    setEditingRound(undefined);
    setConfigOpen(true);
  };

  const openEditPanel = (round: DraftRound) => {
    setEditingRound(round);
    setConfigOpen(true);
  };

  return (
    <div>
      {rounds.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 gap-3 text-muted-foreground">
          <p className="text-sm">暂无面试轮次</p>
          <button
            type="button"
            onClick={openAddPanel}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-500/10 text-primary text-xs hover:bg-teal-500/20 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            添加第一个轮次
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {rounds.map((round, index) => (
            <RoundCard
              key={round.tempId}
              round={round}
              index={index}
              totalCount={rounds.length}
              onEdit={() => openEditPanel(round)}
              onDelete={() => handleDeleteRound(round.tempId)}
              onMoveUp={() => handleMoveUp(index)}
              onMoveDown={() => handleMoveDown(index)}
            />
          ))}
          <button
            type="button"
            onClick={openAddPanel}
            className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg border border-dashed border-border text-muted-foreground text-xs hover:text-foreground hover:border-foreground/20 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            添加轮次
          </button>
        </div>
      )}

      <RoundConfigPanel
        open={configOpen}
        onClose={() => {
          setConfigOpen(false);
          setEditingRound(undefined);
        }}
        initialData={editingRound}
        onSubmit={editingRound ? handleEditRound : handleAddRound}
      />
    </div>
  );
}
