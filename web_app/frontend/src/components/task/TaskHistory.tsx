import { useQuery } from '@tanstack/react-query';
import { listTasks, deleteTask } from '../../api/tasks';
import type { Task } from '../../types/task';
import { Trash2, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface TaskHistoryProps {
  onSelectTask: (task: Task) => void;
  selectedTaskId?: string;
  refreshKey?: number;
}

function truncateTitle(title: string, maxTokens: number = 20): string {
  const tokens = title.split(/\s+/);
  if (tokens.length <= maxTokens) return title;
  return tokens.slice(0, maxTokens).join(' ') + '...';
}

function formatTimestamp(dateStr: string): string {
  const date = new Date(dateStr);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}-${hours}-${minutes}`;
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
              <p className="text-sm text-gray-800 break-words whitespace-normal">{truncateTitle(task.task_description)}</p>
              <div className="flex items-center space-x-2 mt-1">
                <StatusIcon status={task.status} />
                <span className="text-xs text-gray-500">
                  {formatTimestamp(task.created_at)}
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
