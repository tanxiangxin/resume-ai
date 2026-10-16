import { useNavigate } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen items-center justify-center bg-muted">
      <div className="flex flex-col items-center justify-center text-muted-foreground gap-4">
        <FileQuestion className="w-16 h-16 text-muted-foreground/40" strokeWidth={1.5} />
        <div className="text-center">
          <p className="text-lg text-foreground mb-1">页面不存在</p>
          <p className="text-sm text-muted-foreground">您访问的页面可能已被删除或不存在</p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/workspace')}
          className="mt-2 px-4 py-2 rounded-lg bg-teal-500/20 text-primary hover:bg-teal-500/30 transition-colors text-sm"
        >
          返回工作空间列表
        </button>
      </div>
    </div>
  );
}
