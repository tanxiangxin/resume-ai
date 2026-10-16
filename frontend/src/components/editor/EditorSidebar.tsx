import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Plus,
  GripVertical,
  LayoutList,
  Pencil,
  ChevronRight,
  User,
  FileText,
  Briefcase,
  GraduationCap,
  Wrench,
  FolderKanban,
  Award,
  Languages,
  Code,
  QrCode,
} from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useEditorStore } from '@/stores/editor-store';
import { useResumeStore } from '@/stores/resume-store';
import { getSectionTreeItems } from '@/lib/section-items';
import type { ResumeSection } from '@/types/resume';
import { SECTION_TYPES, DEFAULT_SECTION_TITLES, type SectionType } from '@/lib/constants';
import { generateId } from '@/lib/utils';

const sectionIcons: Record<string, React.ElementType> = {
  personal_info: User,
  summary: FileText,
  work_experience: Briefcase,
  education: GraduationCap,
  skills: Wrench,
  projects: FolderKanban,
  certifications: Award,
  languages: Languages,
  github: Code,
  qr_codes: QrCode,
  custom: LayoutList,
};

type DragData =
  | { kind: 'section'; sectionId: string }
  | { kind: 'item'; sectionId: string; itemId: string };

const sectionDndId = (sectionId: string) => `section:${sectionId}`;
const itemDndId = (sectionId: string, itemId: string) => `item:${sectionId}:${itemId}`;

const collisionDetection: CollisionDetection = (args) => {
  const activeData = args.active.data.current as DragData | undefined;
  if (!activeData) return closestCenter(args);

  const droppableContainers = args.droppableContainers.filter((container) => {
    const data = container.data.current as DragData | undefined;
    if (!data || data.kind !== activeData.kind) return false;
    return data.kind !== 'item' || data.sectionId === activeData.sectionId;
  });

  return closestCenter({ ...args, droppableContainers });
};

function SortableTreeItem({
  sectionId,
  item,
  isSelected,
  onSelect,
}: {
  sectionId: string;
  item: ReturnType<typeof getSectionTreeItems>[number];
  isSelected: boolean;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: itemDndId(sectionId, item.id),
    data: { kind: 'item', sectionId, itemId: item.id } satisfies DragData,
  });
  const labelWords = item.label.trim().split(/\s+/);
  const shortLabel = labelWords.length > 1 ? labelWords[0] : Array.from(item.label).slice(0, 10).join('');

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : undefined,
      }}
      className={`group/item flex min-w-0 items-center gap-1.5 rounded-md py-1 pl-7 pr-2 text-left text-xs transition-colors duration-150 ${
        isSelected
          ? 'bg-teal-50 text-teal-700 dark:bg-teal-950/70 dark:text-primary'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      }`}
    >
      <GripVertical
        className="h-3 w-3 shrink-0 cursor-grab text-muted-foreground/40 active:cursor-grabbing"
        {...attributes}
        {...listeners}
      />
      <button
        type="button"
        className="min-w-0 flex-1 truncate text-left"
        title={item.detail ? `${item.label} ${item.detail}` : item.label}
        onClick={onSelect}
      >
        {shortLabel}
      </button>
    </div>
  );
}

function SortableSidebarSection({
  section,
  isSelected,
  isExpanded,
  selectedItemId,
  onSelect,
  onSelectItem,
  onRename,
  onToggleExpanded,
}: {
  section: ResumeSection;
  isSelected: boolean;
  isExpanded: boolean;
  selectedItemId: string | null;
  onSelect: () => void;
  onSelectItem: (itemId: string) => void;
  onRename?: (title: string) => void;
  onToggleExpanded: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: sectionDndId(section.id),
    data: { kind: 'section', sectionId: section.id } satisfies DragData,
  });
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(section.title);
  const inputRef = useRef<HTMLInputElement>(null);
  const items = getSectionTreeItems(section);

  useEffect(() => {
    if (isRenaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isRenaming]);

  const commitRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== section.title && onRename) onRename(trimmed);
    else setRenameValue(section.title);
    setIsRenaming(false);
  };

  const isRenamable = section.type !== 'personal_info';
  const itemIds = items.map((item) => itemDndId(section.id, item.id));

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : undefined,
      }}
    >
      <div
        className={`group/section flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors duration-150 ${
          isSelected
            ? 'bg-teal-50 text-teal-700 dark:bg-teal-950/70 dark:text-primary'
            : 'text-muted-foreground hover:bg-muted dark:hover:bg-muted'
        }`}
      >
        <GripVertical
          className="h-3 w-3 shrink-0 cursor-grab text-muted-foreground/50 active:cursor-grabbing"
          {...attributes}
          {...listeners}
        />
        {items.length > 0 ? (
          <button
            type="button"
            className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground"
            aria-label={isExpanded ? `收起${section.title}` : `展开${section.title}`}
            onClick={(event) => {
              event.stopPropagation();
              onToggleExpanded();
            }}
          >
            <ChevronRight
              className={`h-3.5 w-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            />
          </button>
        ) : (
          <span className="w-4 shrink-0" />
        )}
        <button
          type="button"
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-2"
          onClick={onSelect}
        >
          {(() => {
            const Icon = sectionIcons[section.type] || LayoutList;
            return <Icon className="h-4 w-4 shrink-0" />;
          })()}
          {isRenaming ? (
            <input
              ref={inputRef}
              value={renameValue}
              onChange={(event) => setRenameValue(event.target.value)}
              onBlur={commitRename}
              onKeyDown={(event) => {
                if (event.key === 'Enter') commitRename();
                if (event.key === 'Escape') {
                  setRenameValue(section.title);
                  setIsRenaming(false);
                }
              }}
              onClick={(event) => event.stopPropagation()}
              className="h-5 w-full min-w-0 rounded border border-border bg-transparent px-1 text-sm outline-none"
            />
          ) : (
            <span className="truncate">{section.title}</span>
          )}
        </button>
        {isRenamable && !isRenaming && (
          <button
            type="button"
            className="hidden shrink-0 cursor-pointer rounded p-0.5 text-muted-foreground hover:text-foreground group-hover/section:block"
            onClick={(event) => {
              event.stopPropagation();
              setRenameValue(section.title);
              setIsRenaming(true);
            }}
          >
            <Pencil className="h-3 w-3" />
          </button>
        )}
      </div>

      {isExpanded && items.length > 0 && (
        <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
          <div className="relative my-0.5 space-y-px before:absolute before:bottom-1 before:left-5 before:top-1 before:border-l before:border-border">
            {items.map((item) => (
              <SortableTreeItem
                key={item.id}
                sectionId={section.id}
                item={item}
                isSelected={selectedItemId === item.id}
                onSelect={() => onSelectItem(item.id)}
              />
            ))}
          </div>
        </SortableContext>
      )}
    </div>
  );
}

interface EditorSidebarProps {
  sections: ResumeSection[];
  onAddSection: (section: ResumeSection) => void;
  onReorderSections: (sections: ResumeSection[]) => void;
}

export function EditorSidebar({ sections, onAddSection, onReorderSections }: EditorSidebarProps) {
  const { selectedSectionId, selectedItemId, selectSection, selectItem } = useEditorStore();
  const { updateSectionTitle, reorderSectionItems } = useResumeStore();
  const [expandedSectionIds, setExpandedSectionIds] = useState<Set<string>>(() => new Set());
  const seenSectionIds = useRef(new Set<string>());

  useEffect(() => {
    setExpandedSectionIds((previous) => {
      const next = new Set(previous);
      for (const section of sections) {
        if (seenSectionIds.current.has(section.id)) continue;
        seenSectionIds.current.add(section.id);
        if (getSectionTreeItems(section).length > 0) next.add(section.id);
      }
      return next;
    });
  }, [sections]);

  const handleSelect = useCallback(
    (id: string) => {
      selectSection(id);
      requestAnimationFrame(() => {
        document
          .querySelector<HTMLElement>(`[data-section-id="${id}"]`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    },
    [selectSection],
  );

  const handleSelectItem = useCallback(
    (sectionId: string, itemId: string) => {
      selectSection(sectionId);
      selectItem(itemId);
      setExpandedSectionIds((previous) => new Set(previous).add(sectionId));

      requestAnimationFrame(() => {
        const item = Array.from(document.querySelectorAll<HTMLElement>('[data-section-item-id]')).find(
          (element) => element.dataset.sectionItemId === itemId,
        );
        item?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        requestAnimationFrame(() => item?.querySelector<HTMLElement>('input, textarea, select')?.focus());
      });
    },
    [selectItem, selectSection],
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const activeData = active.data.current as DragData | undefined;
      const overData = over.data.current as DragData | undefined;
      if (!activeData || !overData || activeData.kind !== overData.kind) return;

      if (activeData.kind === 'section' && overData.kind === 'section') {
        const oldIndex = sections.findIndex((section) => section.id === activeData.sectionId);
        const newIndex = sections.findIndex((section) => section.id === overData.sectionId);
        if (oldIndex === -1 || newIndex === -1) return;

        const reordered = [...sections];
        const [moved] = reordered.splice(oldIndex, 1);
        reordered.splice(newIndex, 0, moved);
        onReorderSections(reordered.map((section, index) => ({ ...section, sortOrder: index })));
        return;
      }

      if (
        activeData.kind === 'item' &&
        overData.kind === 'item' &&
        activeData.sectionId === overData.sectionId
      ) {
        reorderSectionItems(activeData.sectionId, activeData.itemId, overData.itemId);
      }
    },
    [onReorderSections, reorderSectionItems, sections],
  );

  const existingTypes = new Set(sections.map((section) => section.type));
  const availableTypes = SECTION_TYPES.filter((type) => type === 'custom' || !existingTypes.has(type));

  const handleAddSection = (type: SectionType) => {
    const newSection: ResumeSection = {
      id: generateId(),
      resumeId: '',
      type,
      title: DEFAULT_SECTION_TITLES[type] || type,
      sortOrder: sections.length,
      visible: true,
      content:
        type === 'personal_info'
          ? { fullName: '', jobTitle: '', email: '', phone: '', location: '' }
          : type === 'summary'
            ? { text: '' }
            : type === 'skills'
              ? { categories: [] }
              : type === 'custom'
                ? { id: '', title: '', date: '', description: '' }
                : { items: [] },
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    onAddSection(newSection);
  };

  return (
    <div className="flex h-full w-56 shrink-0 flex-col border-r border-border bg-background">
      <div className="shrink-0 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">段落</h3>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-0.5 px-2">
          <DndContext
            sensors={sensors}
            collisionDetection={collisionDetection}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={sections.map((section) => sectionDndId(section.id))}
              strategy={verticalListSortingStrategy}
            >
              {sections.map((section) => (
                <SortableSidebarSection
                  key={section.id}
                  section={section}
                  isSelected={selectedSectionId === section.id}
                  isExpanded={expandedSectionIds.has(section.id)}
                  selectedItemId={selectedItemId}
                  onSelect={() => handleSelect(section.id)}
                  onSelectItem={(itemId) => handleSelectItem(section.id, itemId)}
                  onRename={
                    section.type !== 'personal_info'
                      ? (title) => updateSectionTitle(section.id, title)
                      : undefined
                  }
                  onToggleExpanded={() =>
                    setExpandedSectionIds((previous) => {
                      const next = new Set(previous);
                      if (next.has(section.id)) next.delete(section.id);
                      else next.add(section.id);
                      return next;
                    })
                  }
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>

        {availableTypes.length > 0 && (
          <>
            <Separator className="my-3" />
            <div className="px-2 pb-4">
              <p className="mb-2 px-2 text-xs text-muted-foreground">添加段落</p>
              <div className="space-y-0.5">
                {availableTypes.map((type) => {
                  const Icon = sectionIcons[type] || LayoutList;
                  return (
                    <button
                      key={type}
                      type="button"
                      className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-accent-foreground"
                      onClick={() => handleAddSection(type)}
                    >
                      <Plus className="h-3 w-3 shrink-0" />
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{DEFAULT_SECTION_TITLES[type]}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </ScrollArea>
    </div>
  );
}
