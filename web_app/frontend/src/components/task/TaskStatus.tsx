import { useState } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { getTaskStatus } from '../../api/tasks';
import type { Task, TaskStatusUpdate, Message } from '../../types/task';
import LoadingSpinner from '../common/LoadingSpinner';
import MarkdownRenderer from '../common/MarkdownRenderer';
import { CheckCircle, XCircle, Clock, Loader2, Ban, ChevronDown, ChevronUp, Wrench, Search, FileText, MessageSquare, Bot, User } from 'lucide-react';

interface TaskStatusProps {
  task: Task;
  onStatusUpdate?: (status: TaskStatusUpdate) => void;
}

export default function TaskStatus({ task, onStatusUpdate }: TaskStatusProps) {
  const isActive = task.status === 'pending' || task.status === 'running';
  const [showLogs, setShowLogs] = useState(true);
  const [showMessages, setShowMessages] = useState(true);

  const { data: status } = usePolling<TaskStatusUpdate>({
    fetcher: () => getTaskStatus(task.id),
    interval: 2000,
    enabled: isActive,
    shouldStop: (data) =>
      data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled',
    onUpdate: onStatusUpdate,
  });

  const currentStatus = status || {
    ...task,
    recent_logs: [],
    messages: [],
  };

  const messages = (currentStatus as TaskStatusUpdate).messages || [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <StatusBadge status={currentStatus.status} />
        {isActive && task.max_turns > 0 && (
          <span className="text-sm text-gray-500">
            Turn {currentStatus.current_turn}/{task.max_turns}
          </span>
        )}
      </div>

      {/* Question */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <p className="text-sm text-gray-600 font-medium mb-1">Question:</p>
        <p className="text-gray-800">{task.task_description}</p>
      </div>

      {/* Progress */}
      {currentStatus.status === 'running' && (
        <div className="mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <LoadingSpinner size="sm" />
            <span className="text-sm text-gray-600">
              Processing... ({currentStatus.step_count} steps)
            </span>
          </div>
          {task.max_turns > 0 && (
            <div className="bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 rounded-full h-2 transition-all duration-300"
                style={{
                  width: `${Math.min((currentStatus.current_turn / task.max_turns) * 100, 100)}%`,
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* LLM Conversation */}
      {currentStatus.status === 'running' && messages.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowMessages(!showMessages)}
            className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2 hover:text-gray-900"
          >
            {showMessages ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <MessageSquare className="w-4 h-4" />
            <span>Model Conversation ({messages.length})</span>
          </button>

          {showMessages && (
            <div className="space-y-3 max-h-80 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50">
              {messages.map((msg, index) => (
                <MessageBubble key={index} message={msg} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recent Logs - Tool Calls */}
      {currentStatus.status === 'running' && currentStatus.recent_logs && currentStatus.recent_logs.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2 hover:text-gray-900"
          >
            {showLogs ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <Wrench className="w-4 h-4" />
            <span>Tool Calls ({currentStatus.recent_logs.length})</span>
          </button>

          {showLogs && (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {currentStatus.recent_logs.map((log, index) => (
                <LogEntry key={index} log={log as Record<string, unknown>} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pending */}
      {currentStatus.status === 'pending' && (
        <div className="flex items-center space-x-2 text-gray-500">
          <Clock className="w-5 h-5" />
          <span>Waiting to start...</span>
        </div>
      )}

      {/* Error */}
      {currentStatus.status === 'failed' && currentStatus.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <h4 className="text-red-800 font-medium mb-2 flex items-center space-x-2">
            <XCircle className="w-5 h-5" />
            <span>Error</span>
          </h4>
          <pre className="text-sm text-red-600 whitespace-pre-wrap overflow-x-auto">
            {currentStatus.error_message}
          </pre>
        </div>
      )}

      {/* Cancelled */}
      {currentStatus.status === 'cancelled' && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
          <p className="text-gray-600 flex items-center space-x-2">
            <Ban className="w-5 h-5" />
            <span>Task was cancelled</span>
          </p>
        </div>
      )}

      {/* Result */}
      {currentStatus.status === 'completed' && (
        <div className="space-y-4">
          {currentStatus.final_answer && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h4 className="text-green-800 font-medium mb-2 flex items-center space-x-2">
                <CheckCircle className="w-5 h-5" />
                <span>Final Answer</span>
              </h4>
              <p className="text-green-700">{currentStatus.final_answer}</p>
            </div>
          )}
          {currentStatus.summary && (
            <div className="border border-gray-200 rounded-lg p-4">
              <h4 className="font-medium mb-2">Detailed Report</h4>
              <MarkdownRenderer content={currentStatus.summary} />
            </div>
          )}
        </div>
      )}

      {/* Log path */}
      {task.log_path && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-400">Logs: {task.log_path}</p>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isAssistant = message.role === 'assistant';
  const content = message.content || '';

  // Truncate long content
  const displayContent = content.length > 800 ? content.slice(0, 800) + '...' : content;

  return (
    <div className={`flex ${isAssistant ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-[85%] rounded-lg p-3 ${isAssistant ? 'bg-white border border-gray-200' : 'bg-blue-50 border border-blue-200'}`}>
        <div className="flex items-center space-x-2 mb-1">
          {isAssistant ? (
            <Bot className="w-4 h-4 text-purple-500" />
          ) : (
            <User className="w-4 h-4 text-blue-500" />
          )}
          <span className="text-xs font-medium text-gray-500">
            {isAssistant ? 'Assistant' : 'User/Tool'}
          </span>
        </div>
        <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words overflow-x-auto">
          {displayContent}
        </pre>
      </div>
    </div>
  );
}

function LogEntry({ log }: { log: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);

  // Determine log type and extract relevant info
  const logType = (log.type as string) || 'unknown';
  const toolName = (log.tool_name as string) || (log.name as string) || '';
  const serverName = (log.server_name as string) || '';
  const model = (log.model as string) || '';
  const input = log.input || log.arguments || log.args;
  const output = log.output || log.result || log.content;
  const spanPath = (log.path as string) || '';

  // Format value for display
  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') {
      return value.length > 800 ? value.slice(0, 800) + '...' : value;
    }
    const str = JSON.stringify(value, null, 2);
    return str.length > 800 ? str.slice(0, 800) + '...' : str;
  };

  // Get icon based on type
  const getIcon = () => {
    if (logType === 'llm_call' || model) {
      return <Bot className="w-4 h-4 text-green-500" />;
    }
    if (logType === 'tool_call' || toolName) {
      return <Wrench className="w-4 h-4 text-purple-500" />;
    }
    if (toolName.toLowerCase().includes('search')) {
      return <Search className="w-4 h-4 text-blue-500" />;
    }
    if (logType.includes('span')) {
      return <FileText className="w-4 h-4 text-gray-500" />;
    }
    return <FileText className="w-4 h-4 text-gray-400" />;
  };

  // Get title
  const getTitle = () => {
    if (logType === 'llm_call') {
      return model ? `LLM: ${model}` : 'LLM Call';
    }
    if (toolName && serverName) {
      return `${serverName} → ${toolName}`;
    }
    if (toolName) {
      return toolName;
    }
    if (spanPath) {
      return spanPath.split('/').pop() || logType;
    }
    return logType;
  };

  // Get badge color
  const getBadgeColor = () => {
    if (logType === 'llm_call') return 'bg-green-100 text-green-700';
    if (logType === 'tool_call') return 'bg-purple-100 text-purple-700';
    if (logType === 'span_start') return 'bg-blue-100 text-blue-700';
    if (logType === 'span_end') return 'bg-gray-100 text-gray-700';
    return 'bg-gray-100 text-gray-600';
  };

  const title = getTitle();
  const hasDetails = Boolean(input || output);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`w-full flex items-center justify-between p-3 text-left ${hasDetails ? 'hover:bg-gray-50 cursor-pointer' : ''}`}
      >
        <div className="flex items-center space-x-2">
          {getIcon()}
          <span className={`text-xs px-2 py-0.5 rounded ${getBadgeColor()}`}>
            {logType === 'llm_call' ? 'LLM' : logType === 'tool_call' ? 'Tool' : logType.replace('_', ' ')}
          </span>
          <span className="text-sm font-medium text-gray-700 break-words">
            {title}
          </span>
        </div>
        {hasDetails && (
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        )}
      </button>

      {expanded && hasDetails && (
        <div className="border-t border-gray-200 p-3 bg-gray-50 space-y-3">
          {input !== null && input !== undefined && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Input:</p>
              <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {formatValue(input)}
              </pre>
            </div>
          )}
          {output !== null && output !== undefined && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Output:</p>
              <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {formatValue(output)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-800',
  };

  const icons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-4 h-4" />,
    running: <Loader2 className="w-4 h-4 animate-spin" />,
    completed: <CheckCircle className="w-4 h-4" />,
    failed: <XCircle className="w-4 h-4" />,
    cancelled: <Ban className="w-4 h-4" />,
  };

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-sm font-medium ${styles[status] || styles.pending}`}
    >
      {icons[status]}
      <span>{status.charAt(0).toUpperCase() + status.slice(1)}</span>
    </span>
  );
}
