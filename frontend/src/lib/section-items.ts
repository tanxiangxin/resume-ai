import type { ResumeSection } from '@/types/resume';

export type SortableItemCollection = 'items' | 'categories';

export interface SectionTreeItem {
  id: string;
  label: string;
  detail?: string;
}

interface SortableItemSource {
  collection: SortableItemCollection;
  items: Array<Record<string, unknown> & { id: string }>;
}

type ItemLabel = Pick<SectionTreeItem, 'label' | 'detail'>;

const labels: Record<string, (item: Record<string, unknown>) => ItemLabel> = {
  work_experience: (item) => ({
    label: text(item.company) || text(item.position) || '未命名',
    detail: text(item.company) ? text(item.position) : undefined,
  }),
  education: (item) => ({
    label: text(item.institution) || text(item.field) || '未命名',
    detail: text(item.institution) ? text(item.field) : undefined,
  }),
  projects: (item) => ({ label: text(item.name) || '未命名' }),
  certifications: (item) => ({ label: text(item.name) || '未命名' }),
  languages: (item) => ({
    label: text(item.language) || '未命名',
    detail: text(item.proficiency) || undefined,
  }),
  github: (item) => ({ label: text(item.name) || text(item.repoUrl) || '未命名' }),
  qr_codes: (item) => ({ label: text(item.label) || text(item.url) || '未命名' }),
  skills: (item) => ({ label: text(item.name) || '未命名' }),
};

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function getCollectionName(sectionType: string): SortableItemCollection | null {
  if (sectionType === 'skills') return 'categories';
  return labels[sectionType] ? 'items' : null;
}

/** Returns the direct, object-based children that can be reordered within a section. */
export function getSortableItemSource(section: ResumeSection): SortableItemSource | null {
  const collection = getCollectionName(section.type);
  if (!collection) return null;

  const content = section.content as unknown as Record<string, unknown>;
  const value = content[collection];
  if (!Array.isArray(value)) return null;

  if (
    !value.every(
      (item) =>
        typeof item === 'object' && item !== null && typeof item.id === 'string' && item.id.length > 0,
    )
  ) {
    return null;
  }

  const items = value as Array<Record<string, unknown> & { id: string }>;

  return { collection, items };
}

export function getSectionTreeItems(section: ResumeSection): SectionTreeItem[] {
  const source = getSortableItemSource(section);
  const labelItem = labels[section.type];
  if (!source || !labelItem) return [];

  return source.items.map((item) => ({ id: item.id, ...labelItem(item) }));
}
