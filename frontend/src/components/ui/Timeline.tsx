import { VerticalTimeline, VerticalTimelineElement } from 'react-vertical-timeline-component';
import 'react-vertical-timeline-component/style.min.css';
import type { ReactNode } from 'react';

interface TimelineProps {
  children: ReactNode;
  className?: string;
}

interface TimelineItemProps {
  children: ReactNode;
  icon?: ReactNode;
  iconStyle?: React.CSSProperties;
  iconClassName?: string;
  className?: string;
  visible?: boolean;
}

export function Timeline({ children, className }: TimelineProps) {
  return (
    <VerticalTimeline
      layout="1-column-left"
      lineColor="hsl(var(--border))"
      animate={false}
      className={`compact-timeline ${className || ''}`}
    >
      {children}
    </VerticalTimeline>
  );
}

export function TimelineItem({
  children,
  icon,
  iconStyle,
  iconClassName,
  className,
  visible = true,
}: TimelineItemProps) {
  return (
    <VerticalTimelineElement
      className={`compact-timeline-element ${className || ''}`}
      contentStyle={{
        background: 'transparent',
        boxShadow: 'none',
        padding: 0,
      }}
      contentArrowStyle={{ display: 'none' }}
      iconStyle={{
        background: 'transparent',
        boxShadow: 'none',
        ...iconStyle,
      }}
      iconClassName={iconClassName}
      icon={icon}
      visible={visible}
    >
      {children}
    </VerticalTimelineElement>
  );
}
