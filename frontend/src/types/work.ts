export interface WorkTaskMetaInfo extends Record<string, unknown> {
  fileName?: string;
  src?: string;
  template?: string;
  title?: string;
  resumeId?: string;
  resume_id?: string;
  workspaceId?: string;
  workspace_id?: string;
}

export interface WorkTask {
  id: string;
  taskType: string;
  status: string;
  workspaceId?: string;
  metaInfo: WorkTaskMetaInfo | null;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
