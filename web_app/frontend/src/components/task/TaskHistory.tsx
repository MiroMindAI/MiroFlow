import { useQuery } from '@tanstack/react-query';
import { listTasks, deleteTask } from '../../api/tasks';
import type { Task } from '../../types/task';
import { Trash2, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface TaskHistoryProps {
  onSelectTask: (task: Task) => void;
  selectedTaskId?: string;
  refreshKey?: number;
}

export default function TaskHistory({ onSelectTask, selectedTaskId, refreshKey }: TaskHistoryProps) {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tasks', refreshKey],
    queryFn: () => listTasks(1, 50),
    refetchInterval: 5000,
  });

  const handleDelete = async (e: React.MouseEvent, taskId: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this task?')) {
      await deleteTask(taskId);
      refetch();
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-4 text-gray-500">
        <Loader2 className="w-5 h-5 animate-spin mx-auto" />
      </div>
    );
  }

  if (!data?.tasks.length) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p className="text-sm">No tasks yet</p>
        <p className="text-xs mt-1">Submit a question to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {data.tasks.map((task) => (
        <div
          key={task.id}
          onClick={() => onSelectTask(task)}
          className={`p-3 rounded-lg cursor-pointer transition-colors border ${
            selectedTaskId === task.id
              ? 'bg-blue-50 border-blue-200'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 break-words whitespace-normal">{task.task_description}</p>
              <div className="flex items-center space-x-2 mt-1">
                <StatusIcon status={task.status} />
                <span className="text-xs text-gray-500">
                  {formatRelativeTime(task.created_at)}
                </span>
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, task.id)}
              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
              title="Delete task"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />;
    case 'running':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    default:
      return <Clock className="w-4 h-4 text-yellow-500" />;
  }
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
