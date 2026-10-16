import { create } from 'zustand';
import type {
  InterviewCollectionDetail,
  InterviewRound,
  InterviewStatus,
  CreateInterviewCollectionParams,
  CreateInterviewCollectionWithRoundsParams,
  CreateInterviewRoundParams,
  UpdateInterviewRoundParams,
} from '@/types/interview';
import {
  createInterviewCollection,
  createInterviewCollectionWithRounds,
  createInterviewRound,
  listInterviewCollections,
  getInterviewCollection,
  deleteInterviewCollection,
  updateInterviewRound,
  updateInterviewRoundStatus,
  deleteInterviewRound,
} from '@/lib/api';

function computeCollectionStatus(collection: InterviewCollectionDetail): InterviewStatus {
  if (collection.rounds.length === 0) return 'not_started';
  if (collection.rounds.every((r) => r.status === 'completed')) return 'completed';
  if (collection.rounds.some((r) => r.status === 'in_progress')) return 'in_progress';
  return 'not_started';
}

function validateStatusTransition(
  collection: InterviewCollectionDetail,
  roundId: string,
  newStatus: InterviewStatus,
): string | null {
  const round = collection.rounds.find((r) => r.id === roundId);
  if (!round) return 'Round not found';

  const currentStatus = round.status;

  if (currentStatus === newStatus) return null;

  const allowedTransitions: Record<InterviewStatus, InterviewStatus[]> = {
    not_started: ['in_progress'],
    in_progress: ['completed'],
    completed: [],
  };

  if (!allowedTransitions[currentStatus].includes(newStatus)) {
    const validNext = allowedTransitions[currentStatus];
    const validDescriptions = validNext.map((s) => s.replace(/_/g, ' ')).join(' or ');
    if (validNext.length === 0) {
      return `Round "${round.name}" is already completed and cannot transition further.`;
    }
    return `Invalid status transition from "${currentStatus.replace(/_/g, ' ')}" to "${newStatus.replace(/_/g, ' ')}". Round can only transition to ${validDescriptions}.`;
  }

  if (newStatus === 'in_progress') {
    const otherInProgress = collection.rounds.find(
      (r) => r.id !== roundId && r.status === 'in_progress',
    );
    if (otherInProgress) {
      return `Cannot start round "${round.name}" because round "${otherInProgress.name}" is already in progress. Only one round can be in progress at a time.`;
    }

    const sortedRounds = [...collection.rounds].sort((a, b) => a.sortOrder - b.sortOrder);
    const roundIndex = sortedRounds.findIndex((r) => r.id === roundId);

    if (roundIndex > 0) {
      const previousRound = sortedRounds[roundIndex - 1];
      if (previousRound.status !== 'completed') {
        return `Cannot start round "${round.name}" because the previous round "${previousRound.name}" must be completed first.`;
      }
    }
  }

  return null;
}

interface InterviewState {
  // Data
  collections: InterviewCollectionDetail[];
  currentCollectionId: string | null;

  // UI state
  loading: boolean;
  error: string | null;

  // Computed helpers
  currentCollection: () => InterviewCollectionDetail | null;
  getCollectionById: (id: string) => InterviewCollectionDetail | null;

  // Actions
  fetchCollections: (subResumeId: string) => Promise<void>;
  createCollection: (params: CreateInterviewCollectionParams) => Promise<InterviewCollectionDetail>;
  createCollectionWithRounds: (
    params: CreateInterviewCollectionWithRoundsParams,
  ) => Promise<InterviewCollectionDetail>;
  deleteCollection: (id: string) => Promise<void>;
  createRound: (params: CreateInterviewRoundParams) => Promise<InterviewRound>;
  updateRound: (params: UpdateInterviewRoundParams) => Promise<InterviewRound>;
  deleteRound: (id: string) => Promise<void>;
  updateRoundStatus: (
    collectionId: string,
    roundId: string,
    newStatus: InterviewStatus,
  ) => Promise<InterviewRound>;
  clearError: () => void;
  reset: () => void;
}

export const useInterviewStore = create<InterviewState>((set, get) => ({
  collections: [],
  currentCollectionId: null,
  loading: false,
  error: null,

  currentCollection: () => {
    const { collections, currentCollectionId } = get();
    if (!currentCollectionId) return null;
    return collections.find((c) => c.id === currentCollectionId) ?? null;
  },

  getCollectionById: (id: string) => {
    const { collections } = get();
    return collections.find((c) => c.id === id) ?? null;
  },

  fetchCollections: async (subResumeId: string) => {
    set({ loading: true, error: null });
    try {
      const collections = await listInterviewCollections(subResumeId);
      const collectionsWithRounds = await Promise.all(
        collections.map(async (col) => {
          try {
            const rounds = await getInterviewCollection(col.id);
            return {
              ...col,
              rounds,
              status: computeCollectionStatus({ ...col, rounds }),
            };
          } catch {
            return { ...col, rounds: [] } as InterviewCollectionDetail;
          }
        }),
      );
      const { currentCollectionId } = get();
      set({
        collections: Array.isArray(collectionsWithRounds) ? collectionsWithRounds : [],
        currentCollectionId:
          currentCollectionId ??
          (Array.isArray(collectionsWithRounds) && collectionsWithRounds.length > 0
            ? collectionsWithRounds[0].id
            : null),
        loading: false,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to fetch interview collections',
        loading: false,
      });
    }
  },

  createCollection: async (params: CreateInterviewCollectionParams) => {
    set({ error: null });
    try {
      const created = await createInterviewCollection(params);
      const newCollection: InterviewCollectionDetail = {
        ...created,
        rounds: [],
      };
      set((state) => ({
        collections: [...state.collections, newCollection],
        currentCollectionId: state.currentCollectionId ?? newCollection.id,
      }));
      return newCollection;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to create interview collection',
      });
      throw err;
    }
  },

  deleteCollection: async (id: string) => {
    set({ error: null });
    try {
      await deleteInterviewCollection(id);
      set((state) => {
        const updatedCollections = state.collections.filter((c) => c.id !== id);
        return {
          collections: updatedCollections,
          currentCollectionId:
            state.currentCollectionId === id
              ? updatedCollections.length > 0
                ? updatedCollections[0].id
                : null
              : state.currentCollectionId,
        };
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to delete interview collection',
      });
      throw err;
    }
  },

  createCollectionWithRounds: async (params: CreateInterviewCollectionWithRoundsParams) => {
    set({ error: null });
    try {
      const created = await createInterviewCollectionWithRounds(params);
      let rounds: InterviewRound[] = [];
      try {
        rounds = await getInterviewCollection(created.id);
      } catch {}
      const collectionWithRounds: InterviewCollectionDetail = {
        ...created,
        rounds,
        status: computeCollectionStatus({ ...created, rounds }),
      };
      set((state) => ({
        collections: [...state.collections, collectionWithRounds],
        currentCollectionId: state.currentCollectionId ?? collectionWithRounds.id,
      }));
      return collectionWithRounds;
    } catch (err) {
      set({
        error:
          err instanceof Error ? err.message : 'Failed to create interview collection with rounds',
      });
      throw err;
    }
  },

  createRound: async (params: CreateInterviewRoundParams) => {
    set({ error: null });
    try {
      const created = await createInterviewRound(params);
      set((state) => ({
        collections: state.collections.map((c) => {
          if (c.id !== params.interviewCollectionId) return c;
          const updatedRounds = [...c.rounds, created].sort((a, b) => a.sortOrder - b.sortOrder);
          return {
            ...c,
            rounds: updatedRounds,
            status: computeCollectionStatus({ ...c, rounds: updatedRounds }),
          };
        }),
      }));
      return created;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to create interview round',
      });
      throw err;
    }
  },

  updateRound: async (params: UpdateInterviewRoundParams) => {
    set({ error: null });
    try {
      const updated = await updateInterviewRound(params);
      set((state) => ({
        collections: state.collections.map((c) => ({
          ...c,
          rounds: c.rounds.map((r) => (r.id === params.id ? updated : r)),
        })),
      }));
      return updated;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update interview round',
      });
      throw err;
    }
  },

  deleteRound: async (id: string) => {
    set({ error: null });
    try {
      await deleteInterviewRound(id);
      set((state) => ({
        collections: state.collections.map((c) => {
          const updatedRounds = c.rounds.filter((r) => r.id !== id);
          if (updatedRounds.length === c.rounds.length) return c;
          return {
            ...c,
            rounds: updatedRounds,
            status: computeCollectionStatus({ ...c, rounds: updatedRounds }),
          };
        }),
      }));
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to delete interview round',
      });
      throw err;
    }
  },

  updateRoundStatus: async (collectionId: string, roundId: string, newStatus: InterviewStatus) => {
    const { collections } = get();
    const collection = collections.find((c) => c.id === collectionId);

    if (!collection) {
      set({ error: `Collection with id "${collectionId}" not found.` });
      throw new Error(`Collection with id "${collectionId}" not found.`);
    }

    const validationError = validateStatusTransition(collection, roundId, newStatus);
    if (validationError) {
      set({ error: validationError });
      throw new Error(validationError);
    }

    set({ error: null });
    try {
      const updated = await updateInterviewRoundStatus({
        roundId,
        status: newStatus,
      });

      set((state) => ({
        collections: state.collections.map((c) => {
          if (c.id !== collectionId) return c;

          const updatedRounds = c.rounds.map((r) => (r.id === roundId ? updated : r));

          return {
            ...c,
            rounds: updatedRounds,
            status: computeCollectionStatus({ ...c, rounds: updatedRounds }),
          };
        }),
      }));

      return updated;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to update round status',
      });
      throw err;
    }
  },

  clearError: () => {
    set({ error: null });
  },

  reset: () => {
    set({
      collections: [],
      currentCollectionId: null,
      loading: false,
      error: null,
    });
  },
}));
