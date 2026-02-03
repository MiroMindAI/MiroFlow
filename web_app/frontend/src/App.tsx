import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Bot, Send, Plus, Trash2, Loader2, Menu, X, Square, Paperclip, File } from 'lucide-react';
import { createTask, listTasks, getTask, getTaskStatus, deleteTask, listConfigs, uploadFile } from './api/tasks';
import { usePolling } from './hooks/usePolling';
import type { TaskStatusUpdate, UploadResponse, FileInfo } from './types/task';
import MarkdownRenderer from './components/common/MarkdownRenderer';

export default function App() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch configs
  const { data: configData } = useQuery({
    queryKey: ['configs'],
    queryFn: listConfigs,
  });

  // Fetch task list
  const { data: taskList, refetch: refetchTasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => listTasks(1, 50),
    refetchInterval: 5000,
  });

  // Fetch selected task
  const { data: selectedTask, refetch: refetchSelectedTask } = useQuery({
    queryKey: ['task', selectedTaskId],
    queryFn: () => (selectedTaskId ? getTask(selectedTaskId) : null),
    enabled: !!selectedTaskId,
  });

  // Check if any task is currently running
  const runningTask = taskList?.tasks.find(t => t.status === 'running' || t.status === 'pending');
  const isAnyTaskRunning = !!runningTask;

  // Poll for status updates only when selected task is running
  const isSelectedTaskActive = selectedTask?.status === 'pending' || selectedTask?.status === 'running';

  const { data: statusUpdate } = usePolling<TaskStatusUpdate>({
    fetcher: () => getTaskStatus(selectedTaskId!),
    interval: 1500,
    enabled: !!selectedTaskId && isSelectedTaskActive,
    shouldStop: (data) =>
      data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled',
  });

  // Create task mutation
  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: (task) => {
      setSelectedTaskId(task.id);
      setInputValue('');
      setUploadedFile(null);
      setUserScrolledUp(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      refetchTasks();
    },
  });

  // Handle file selection
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await uploadFile(file);
      setUploadedFile(result);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Delete task mutation
  const deleteMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: (_, deletedTaskId) => {
      if (selectedTaskId === deletedTaskId) {
        setSelectedTaskId(null);
      }
      refetchTasks();
    },
  });

  // Cancel/Stop task mutation
  const cancelMutation = useMutation({
    mutationFn: deleteTask,
    onSuccess: () => {
      refetchTasks();
      refetchSelectedTask();
    },
  });

  // Handle scroll - detect if user scrolled up (with throttling)
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleScroll = useCallback(() => {
    if (scrollTimeoutRef.current) return; // Throttle scroll events

    scrollTimeoutRef.current = setTimeout(() => {
      const container = messagesContainerRef.current;
      if (container) {
        const { scrollTop, scrollHeight, clientHeight } = container;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
        setUserScrolledUp(!isNearBottom);
      }
      scrollTimeoutRef.current = null;
    }, 100);
  }, []);

  // Auto-scroll only when running and user hasn't scrolled up
  useEffect(() => {
    if (isSelectedTaskActive && !userScrolledUp) {
      const container = messagesContainerRef.current;
      if (container) {
        // Use requestAnimationFrame for smooth scrolling without jank
        requestAnimationFrame(() => {
          // Double-check scroll position right before scrolling to avoid
          // race condition with throttled scroll detection
          const { scrollTop, scrollHeight, clientHeight } = container;
          const isNearBottom = scrollHeight - scrollTop - clientHeight < 200;
          if (isNearBottom) {
            container.scrollTop = container.scrollHeight;
          }
        });
      }
    }
  }, [statusUpdate?.messages, statusUpdate?.recent_logs, isSelectedTaskActive, userScrolledUp]);

  // Reset scroll state when switching tasks
  useEffect(() => {
    setUserScrolledUp(false);
  }, [selectedTaskId]);

  // Refresh when status changes to completed/failed
  useEffect(() => {
    if (statusUpdate?.status === 'completed' || statusUpdate?.status === 'failed' || statusUpdate?.status === 'cancelled') {
      refetchTasks();
      refetchSelectedTask();
    }
  }, [statusUpdate?.status, refetchTasks, refetchSelectedTask]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || createMutation.isPending || isAnyTaskRunning || isUploading) return;

    createMutation.mutate({
      task_description: inputValue,
      config_path: configData?.default || 'config/agent_gradio_demo.yaml',
      file_id: uploadedFile?.file_id,
    });
  };

  const handleNewChat = () => {
    setSelectedTaskId(null);
    setInputValue('');
  };

  const handleDeleteTask = (taskId: string) => {
    if (confirm('Delete this conversation?')) {
      deleteMutation.mutate(taskId);
    }
  };

  const handleStopTask = () => {
    if (runningTask) {
      cancelMutation.mutate(runningTask.id);
    }
  };

  // For running tasks, use statusUpdate; for completed tasks, use selectedTask
  const currentStatus = isSelectedTaskActive ? (statusUpdate || selectedTask) : selectedTask;
  const messages = isSelectedTaskActive ? ((statusUpdate as TaskStatusUpdate)?.messages || []) : [];

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} flex-shrink-0 bg-white border-r border-gray-200 transition-all duration-300 overflow-hidden`}>
        <div className="flex flex-col h-full p-2">
          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            disabled={isAnyTaskRunning}
            className={`flex items-center gap-3 w-full p-3 rounded-lg border border-gray-300 transition-colors mb-2 ${
              isAnyTaskRunning
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'hover:bg-gray-100 text-gray-700'
            }`}
          >
            <Plus className="w-4 h-4" />
            <span>New chat</span>
          </button>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto space-y-1">
            {taskList?.tasks.map((task) => (
              <div
                key={task.id}
                className={`group flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedTaskId === task.id
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-gray-100'
                }`}
                onClick={() => setSelectedTaskId(task.id)}
              >
                <div className="flex-1 text-sm text-gray-700 break-words whitespace-normal">
                  {task.task_description}
                </div>
                {(task.status === 'running' || task.status === 'pending') && (
                  <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteTask(task.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="flex items-center gap-4 p-4 border-b border-gray-200 bg-white">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {sidebarOpen ? <X className="w-5 h-5 text-gray-600" /> : <Menu className="w-5 h-5 text-gray-600" />}
          </button>
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-blue-600" />
            <span className="font-semibold text-gray-800">MiroFlow</span>
          </div>
          {currentStatus && (
            <div className="ml-auto flex items-center gap-3 text-sm">
              {(currentStatus.status === 'running' || currentStatus.status === 'pending') && (
                <>
                  <div className="flex items-center gap-2 text-blue-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Turn {currentStatus.current_turn} • {currentStatus.step_count} steps</span>
                  </div>
                  <button
                    onClick={handleStopTask}
                    disabled={cancelMutation.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    <span>Stop</span>
                  </button>
                </>
              )}
              {currentStatus.status === 'completed' && (
                <span className="text-green-600 font-medium">Completed</span>
              )}
              {currentStatus.status === 'failed' && (
                <span className="text-red-600 font-medium">Failed</span>
              )}
              {currentStatus.status === 'cancelled' && (
                <span className="text-gray-500 font-medium">Stopped</span>
              )}
            </div>
          )}
        </header>

        {/* Messages Area */}
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto bg-gray-50 scroll-smooth overscroll-contain"
          style={{ willChange: 'scroll-position' }}
        >
          {!selectedTask ? (
            // Welcome Screen
            <div className="h-full flex flex-col items-center justify-center p-8">
              <Bot className="w-16 h-16 text-blue-500 mb-6" />
              <h1 className="text-2xl font-semibold text-gray-800 mb-2">MiroFlow</h1>
              <p className="text-gray-500 text-center max-w-md">
                AI Research Agent for complex tasks. Enter your question below to get started.
              </p>
              {isAnyTaskRunning && (
                <div className="mt-4 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
                  A task is currently running. Please wait for it to complete.
                </div>
              )}
            </div>
          ) : (
            // Conversation View
            <div className="max-w-3xl mx-auto p-4 space-y-6">
              {/* User Question */}
              <MessageBubble
                role="user"
                content={selectedTask.task_description}
                fileInfo={selectedTask.file_info}
              />

              {/* Agent Messages (only for running tasks) */}
              {messages.map((msg, index) => (
                <MessageBubble key={index} role={msg.role} content={msg.content} />
              ))}

              {/* Running Status */}
              {currentStatus?.status === 'running' && (
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-gray-500">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                    {statusUpdate?.recent_logs && statusUpdate.recent_logs.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {statusUpdate.recent_logs.slice(-5).map((log, index) => (
                          <LogItem key={index} log={log as Record<string, unknown>} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Final Answer - show for completed tasks */}
              {currentStatus?.status === 'completed' && currentStatus.final_answer && (
                <MessageBubble
                  role="assistant"
                  content={`**Final Answer:**\n\n${currentStatus.final_answer}`}
                  isAnswer
                />
              )}

              {/* Summary - show for completed tasks */}
              {currentStatus?.status === 'completed' && currentStatus.summary && (
                <MessageBubble
                  role="assistant"
                  content={`**Detailed Report:**\n\n${currentStatus.summary}`}
                />
              )}

              {/* Error */}
              {currentStatus?.status === 'failed' && currentStatus.error_message && (
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex-1">
                    <p className="text-red-700 font-medium mb-2">Error</p>
                    <pre className="text-sm text-red-600 whitespace-pre-wrap">
                      {currentStatus.error_message}
                    </pre>
                  </div>
                </div>
              )}

              {/* Cancelled */}
              {currentStatus?.status === 'cancelled' && (
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-gray-400 flex items-center justify-center flex-shrink-0">
                    <Square className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 flex-1">
                    <p className="text-gray-600">Task was stopped.</p>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-white">
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
            {/* Attached file display */}
            {uploadedFile && (
              <div className="mb-2 flex items-center gap-2 p-2 bg-gray-50 border border-gray-200 rounded-lg">
                <File className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700 flex-1 truncate">{uploadedFile.file_name}</span>
                <span className="text-xs text-gray-400">({uploadedFile.file_type})</span>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="p-1 hover:bg-gray-200 rounded transition-colors"
                  title="Remove file"
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            )}
            <div className="relative flex items-end gap-2">
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                accept=".xlsx,.xls,.csv,.pdf,.doc,.docx,.txt,.json,.png,.jpg,.jpeg,.mp3,.wav,.mp4"
              />
              {/* Attachment button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isAnyTaskRunning || isUploading}
                className={`p-3 rounded-xl border transition-colors flex-shrink-0 ${
                  isAnyTaskRunning || isUploading
                    ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                }`}
                title="Attach file"
              >
                {isUploading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Paperclip className="w-5 h-5" />
                )}
              </button>
              {/* Text input */}
              <div className="relative flex-1">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder={isAnyTaskRunning ? "Please wait for current task to complete..." : "Message MiroFlow..."}
                  disabled={isAnyTaskRunning}
                  rows={1}
                  className={`w-full border rounded-xl px-4 py-3 pr-12 resize-none focus:outline-none placeholder-gray-400 ${
                    isAnyTaskRunning
                      ? 'bg-gray-100 border-gray-200 text-gray-500 cursor-not-allowed'
                      : 'bg-white border-gray-300 focus:border-blue-400 focus:ring-2 focus:ring-blue-100'
                  }`}
                  style={{ minHeight: '52px', maxHeight: '200px' }}
                />
                <button
                  type="submit"
                  disabled={!inputValue.trim() || createMutation.isPending || isAnyTaskRunning || isUploading}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
                >
                  {createMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-400 text-center mt-2">
              MiroFlow can make mistakes. Verify important information.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ role, content, isAnswer, fileInfo }: { role: string; content: string; isAnswer?: boolean; fileInfo?: FileInfo | null }) {
  const isUser = role === 'user';

  return (
    <div className="flex items-start gap-4">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-gray-700' : 'bg-blue-500'
      }`}>
        {isUser ? (
          <span className="text-sm font-medium text-white">U</span>
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>
      <div className={`flex-1 ${isAnswer ? 'bg-green-50 border border-green-200 rounded-lg p-4' : ''}`}>
        {/* Display attached file for user messages */}
        {isUser && fileInfo && (
          <div className="mb-2 inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg">
            <File className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-700">{fileInfo.file_name}</span>
            <span className="text-xs text-gray-400">({fileInfo.file_type})</span>
          </div>
        )}
        <div className="prose prose-sm max-w-none text-gray-800">
          <MarkdownRenderer content={content} />
        </div>
      </div>
    </div>
  );
}

function LogItem({ log }: { log: Record<string, unknown> }) {
  const logType = (log.type as string) || '';
  const toolName = (log.tool_name as string) || (log.name as string) || '';
  const serverName = (log.server_name as string) || '';

  let label = '';
  let color = 'text-gray-500';

  if (logType === 'tool_call' || toolName) {
    label = serverName ? `${serverName} → ${toolName}` : toolName;
    color = 'text-purple-600';
  } else if (logType === 'llm_call') {
    label = `LLM: ${(log.model as string) || 'call'}`;
    color = 'text-green-600';
  } else if (logType === 'span_start') {
    label = `Starting: ${(log.name as string) || ''}`;
    color = 'text-blue-500';
  } else if (logType === 'span_end') {
    label = `Completed: ${(log.name as string) || ''}`;
    color = 'text-gray-400';
  } else {
    return null;
  }

  return (
    <div className={`text-xs ${color} flex items-center gap-2`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      <span>{label}</span>
    </div>
  );
}
