import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Bot, Send, Plus, Trash2, Loader2, Menu, X, Square, Paperclip, File, ChevronDown, ChevronRight, Brain, Search, Globe, Code, Lightbulb, Wrench, List, CheckCircle } from 'lucide-react';
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
  const [accumulatedMessages, setAccumulatedMessages] = useState<Array<{ role: string; content: string }>>([]);
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
  const isSelectedTaskCompleted = selectedTask?.status === 'completed' || selectedTask?.status === 'failed' || selectedTask?.status === 'cancelled';

  const { data: statusUpdate } = usePolling<TaskStatusUpdate>({
    fetcher: () => getTaskStatus(selectedTaskId!),
    interval: 1500,
    enabled: !!selectedTaskId && isSelectedTaskActive,
    shouldStop: (data) =>
      data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled',
  });

  // Fetch status once for completed tasks to get messages history
  const { data: completedTaskStatus } = useQuery({
    queryKey: ['taskStatus', selectedTaskId],
    queryFn: () => getTaskStatus(selectedTaskId!),
    enabled: !!selectedTaskId && isSelectedTaskCompleted,
    staleTime: Infinity, // Don't refetch since completed tasks don't change
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

  // Reset scroll state and accumulated messages when switching tasks
  useEffect(() => {
    setUserScrolledUp(false);
    setAccumulatedMessages([]);
  }, [selectedTaskId]);

  // Accumulate messages from status updates - merge new messages into accumulated
  useEffect(() => {
    if (statusUpdate?.messages && statusUpdate.messages.length > 0) {
      setAccumulatedMessages(prev => {
        // Create a map of existing messages by content hash for deduplication
        const existingContents = new Set(prev.map(m => m.content));
        const newMessages = statusUpdate.messages.filter(
          (m: { role: string; content: string }) => !existingContents.has(m.content)
        );
        if (newMessages.length > 0) {
          return [...prev, ...newMessages];
        }
        return prev;
      });
    }
  }, [statusUpdate?.messages]);

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
  // Use accumulated messages for running tasks, or merge accumulated + completed status messages
  // This ensures we don't lose the full history when task transitions from running to completed
  const messages = (() => {
    if (isSelectedTaskActive) {
      return accumulatedMessages;
    }
    // For completed tasks, merge accumulated messages with fetched messages
    const fetchedMessages = completedTaskStatus?.messages || [];
    if (accumulatedMessages.length === 0) {
      return fetchedMessages;
    }
    if (fetchedMessages.length === 0) {
      return accumulatedMessages;
    }
    // Merge and deduplicate by content
    const contentSet = new Set(accumulatedMessages.map(m => m.content));
    const additionalMessages = fetchedMessages.filter(
      (m: { role: string; content: string }) => !contentSet.has(m.content)
    );
    return [...accumulatedMessages, ...additionalMessages];
  })();

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

              {/* Running state: Show all messages with thinking expanded */}
              {(currentStatus?.status === 'running' || currentStatus?.status === 'pending') && (
                <>
                  {messages.map((msg, index) => (
                    <MessageBubble key={index} role={msg.role} content={msg.content} isRunning={true} />
                  ))}
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
                </>
              )}

              {/* Completed state: Show collapsed thinking trajectory, then summary */}
              {currentStatus?.status === 'completed' && (
                <CompletedView
                  messages={messages}
                  finalAnswer={currentStatus.final_answer || undefined}
                  summary={currentStatus.summary || undefined}
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

// Parse content to extract thinking blocks, tool calls, and regular text
interface ParsedContent {
  thinking: string | null;
  toolCalls: Array<{ name: string; args: string; result?: string }>;
  text: string;
}

function parseMessageContent(content: string): ParsedContent {
  let thinking: string | null = null;
  const toolCalls: Array<{ name: string; args: string; result?: string }> = [];
  let text = content;

  // Extract thinking block - handle both complete and incomplete (streaming/truncated) cases
  // Case 1: Complete <think>...</think> block
  const completeThinkMatch = text.match(/<think>([\s\S]*?)<\/think>/i);
  if (completeThinkMatch) {
    thinking = completeThinkMatch[1].trim();
    text = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  } else {
    // Case 2: Incomplete - starts with <think> but no closing tag (streaming/truncated)
    const incompleteThinkMatch = text.match(/^<think>([\s\S]*)$/i);
    if (incompleteThinkMatch) {
      thinking = incompleteThinkMatch[1].trim();
      text = '';
    } else {
      // Case 3: Has <think> somewhere but no closing tag
      const partialThinkMatch = text.match(/<think>([\s\S]*)$/i);
      if (partialThinkMatch) {
        thinking = partialThinkMatch[1].trim();
        text = text.replace(/<think>[\s\S]*$/i, '').trim();
      }
    }
  }

  // Extract tool calls - MCP format: <use_mcp_tool>...</use_mcp_tool>
  // Complete tool calls with closing tag
  const mcpToolRegex = /<use_mcp_tool[^>]*>\s*<server_name[^>]*>(.*?)<\/server_name>\s*<tool_name[^>]*>(.*?)<\/tool_name>\s*<arguments[^>]*>\s*([\s\S]*?)\s*<\/arguments>\s*<\/use_mcp_tool>/gi;
  let match: RegExpExecArray | null;
  while ((match = mcpToolRegex.exec(text)) !== null) {
    const serverName = match[1].trim();
    const toolName = match[2].trim();
    const args = match[3].trim();
    toolCalls.push({
      name: serverName ? `${serverName} → ${toolName}` : toolName,
      args
    });
  }
  text = text.replace(/<use_mcp_tool[^>]*>[\s\S]*?<\/use_mcp_tool>/gi, '').trim();

  // Incomplete MCP tool calls (streaming/truncated) - no closing </use_mcp_tool>
  const incompleteMcpRegex = /<use_mcp_tool[^>]*>\s*(?:<server_name[^>]*>(.*?)<\/server_name>)?\s*(?:<tool_name[^>]*>(.*?)<\/tool_name>)?\s*(?:<arguments[^>]*>\s*([\s\S]*))?$/gi;
  while ((match = incompleteMcpRegex.exec(text)) !== null) {
    const serverName = match[1]?.trim() || '';
    const toolName = match[2]?.trim() || 'pending...';
    const args = match[3]?.trim() || '';
    if (serverName || toolName !== 'pending...') {
      toolCalls.push({
        name: serverName ? `${serverName} → ${toolName}` : toolName,
        args: args || '(loading...)'
      });
    }
  }
  text = text.replace(/<use_mcp_tool[^>]*>[\s\S]*$/gi, '').trim();

  // Tool result blocks
  const toolResultRegex = /<tool_result>\s*(\w+):\s*([\s\S]*?)<\/tool_result>/gi;
  let resultMatch: RegExpExecArray | null;
  while ((resultMatch = toolResultRegex.exec(text)) !== null) {
    const toolName = resultMatch[1];
    const toolResult = resultMatch[2].trim();
    const existingTool = toolCalls.find(t => t.name.includes(toolName));
    if (existingTool) {
      existingTool.result = toolResult;
    } else {
      toolCalls.push({ name: toolName, args: '', result: toolResult });
    }
  }
  text = text.replace(/<tool_result>[\s\S]*?<\/tool_result>/gi, '').trim();

  return { thinking, toolCalls, text };
}

// Thinking section - foldable with 2-line preview (for running state)
function ThinkingSection({ content, defaultExpanded = false }: { content: string; defaultExpanded?: boolean }) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Get first 2 lines for preview
  const lines = content.split('\n');
  const preview = lines.slice(0, 2).join('\n');
  const hasMore = lines.length > 2 || preview.length < content.length;

  return (
    <div className="border rounded-lg overflow-hidden bg-white border-gray-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <Brain className="w-4 h-4" />
        <span>Thinking</span>
      </button>
      <div className="px-3 py-2 border-t border-gray-200 bg-white overflow-hidden">
        <pre className={`text-sm text-gray-700 whitespace-pre-wrap leading-relaxed overflow-hidden ${!isExpanded ? 'line-clamp-2' : ''}`} style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
          {isExpanded ? content : preview}
        </pre>
        {!isExpanded && hasMore && (
          <span className="text-xs text-gray-500">...</span>
        )}
      </div>
    </div>
  );
}

// Summary section header (for completed state)
function SummaryHeader() {
  return (
    <div className="flex items-center justify-center gap-2 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg">
      <CheckCircle className="w-4 h-4" />
      <span>Summary</span>
    </div>
  );
}

// Completed view - handles all parsing and displays thinking trajectory + summary
function CompletedView({
  messages,
  finalAnswer,
  summary
}: {
  messages: Array<{ role: string; content: string }>;
  finalAnswer?: string;
  summary?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Check if there's any content to show in the trajectory
  const hasThinkingContent = messages.some(msg => {
    if (msg.role === 'user') return false;
    const parsed = parseMessageContent(msg.content);
    // Show trajectory if there's any thinking, tool calls, or text content
    return parsed.thinking || parsed.toolCalls.length > 0 || parsed.text;
  });

  // Parse final answer and summary
  const parsedFinalAnswer = finalAnswer ? parseMessageContent(finalAnswer) : null;
  const parsedSummary = summary ? parseMessageContent(summary) : null;

  // Check if final answer or summary has thinking
  const hasThinkingInAnswer = !!parsedFinalAnswer?.thinking || !!parsedSummary?.thinking;

  // Get clean content without think tags
  const cleanFinalAnswer = parsedFinalAnswer?.text || '';
  const cleanSummary = parsedSummary?.text || '';

  return (
    <>
      {/* Thinking Trajectory - collapsed by default, transparent/borderless style */}
      {(hasThinkingContent || hasThinkingInAnswer) && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
          >
            <List className="w-4 h-4" />
            <span>{isExpanded ? 'Hide' : 'Show'} thinking trajectory</span>
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          {isExpanded && (
            <div className="space-y-6 pt-4">
              {/* Render each message with full ThinkingSection and ToolCallDisplay */}
              {messages.map((msg, index) => {
                if (msg.role === 'user') return null;
                const parsed = parseMessageContent(msg.content);
                // Show ALL messages - don't filter out those without thinking/toolCalls
                // This ensures full trace is visible exactly as during running state
                const hasAnyContent = parsed.thinking || parsed.toolCalls.length > 0 || parsed.text;
                if (!hasAnyContent) return null;

                return (
                  <div key={index} className="space-y-3">
                    {/* Thinking section - same style as running state */}
                    {parsed.thinking && (
                      <ThinkingSection content={parsed.thinking} defaultExpanded={false} />
                    )}

                    {/* Tool calls - same style as running state */}
                    {parsed.toolCalls.length > 0 && (
                      <div className="space-y-3">
                        {parsed.toolCalls.map((tool, idx) => (
                          <ToolCallDisplay key={idx} tool={tool} />
                        ))}
                      </div>
                    )}

                    {/* Text content - show any non-thinking, non-tool text */}
                    {parsed.text && (
                      <SmartTextContent content={parsed.text} />
                    )}
                  </div>
                );
              })}

              {/* Thinking from final answer */}
              {parsedFinalAnswer?.thinking && (
                <ThinkingSection content={parsedFinalAnswer.thinking} defaultExpanded={false} />
              )}

              {/* Thinking from summary */}
              {parsedSummary?.thinking && (
                <ThinkingSection content={parsedSummary.thinking} defaultExpanded={false} />
              )}
            </div>
          )}
        </div>
      )}

      {/* Summary Header */}
      <SummaryHeader />

      {/* Final Answer - parsed to remove think tags */}
      {cleanFinalAnswer && (
        <div className="prose prose-sm max-w-none text-gray-800">
          <MarkdownRenderer content={cleanFinalAnswer} />
        </div>
      )}

      {/* Detailed Report - parsed to remove think tags */}
      {cleanSummary && (
        <div className="prose prose-sm max-w-none text-gray-800">
          <MarkdownRenderer content={cleanSummary} />
        </div>
      )}
    </>
  );
}

function MessageBubble({ role, content, isAnswer, fileInfo, isRunning }: { role: string; content: string; isAnswer?: boolean; fileInfo?: FileInfo | null; isRunning?: boolean }) {
  const isUser = role === 'user';
  const parsed = isUser ? null : parseMessageContent(content);

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
      <div className={`flex-1 space-y-3 ${isAnswer ? 'bg-green-50 border border-green-200 rounded-lg p-4' : ''}`}>
        {/* Display attached file for user messages */}
        {isUser && fileInfo && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg">
            <File className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-700">{fileInfo.file_name}</span>
            <span className="text-xs text-gray-400">({fileInfo.file_type})</span>
          </div>
        )}

        {/* For user messages, use SmartTextContent to handle embedded search results */}
        {isUser && (
          <SmartTextContent content={content} />
        )}

        {/* For assistant messages, show parsed content */}
        {!isUser && parsed && (
          <>
            {/* Thinking section - expanded during running, foldable when not */}
            {parsed.thinking && (
              <ThinkingSection content={parsed.thinking} defaultExpanded={isRunning} />
            )}

            {/* Tool calls - clean display */}
            {parsed.toolCalls.length > 0 && (
              <div className="space-y-3">
                {parsed.toolCalls.map((tool, idx) => (
                  <ToolCallDisplay key={idx} tool={tool} />
                ))}
              </div>
            )}

            {/* Main text content - with smart detection for search results */}
            {parsed.text && (
              <SmartTextContent content={parsed.text} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Smart text content - detects and formats search results in text
function SmartTextContent({ content }: { content: string }) {
  // Try to detect if the content is or contains search result JSON
  const parseSearchResults = (text: string): { results: Array<{ title?: string; link?: string; url?: string; snippet?: string }> | null; remainingText: string } => {
    // Try to find JSON in the text
    const jsonMatch = text.match(/\{[\s\S]*"organic"[\s\S]*\}/);
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0]);
        if (parsed.organic && Array.isArray(parsed.organic)) {
          const remainingText = text.replace(jsonMatch[0], '').trim();
          return { results: parsed.organic, remainingText };
        }
      } catch {
        // Not valid JSON
      }
    }

    // Try other formats
    const altJsonMatch = text.match(/\{[\s\S]*"organic_results"[\s\S]*\}/) || text.match(/\{[\s\S]*"results"[\s\S]*\}/);
    if (altJsonMatch) {
      try {
        const parsed = JSON.parse(altJsonMatch[0]);
        const results = parsed.organic_results || parsed.results;
        if (Array.isArray(results)) {
          const remainingText = text.replace(altJsonMatch[0], '').trim();
          return { results, remainingText };
        }
      } catch {
        // Not valid JSON
      }
    }

    return { results: null, remainingText: text };
  };

  const { results: searchResults, remainingText } = parseSearchResults(content);

  if (searchResults && searchResults.length > 0) {
    return (
      <div className="space-y-4">
        {/* Render remaining text if any */}
        {remainingText && (
          <div className="prose prose-sm max-w-none text-gray-800">
            <MarkdownRenderer content={remainingText} />
          </div>
        )}

        {/* Render search results */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <List className="w-3 h-3" />
            <span>Found {searchResults.length} results</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {searchResults.slice(0, 10).map((result, idx) => {
              const resultUrl = result.link || result.url || '';
              let faviconUrl = '';
              if (resultUrl) {
                try {
                  const domain = new URL(resultUrl).hostname;
                  faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
                } catch {
                  // Invalid URL
                }
              }
              return (
                <a
                  key={idx}
                  href={resultUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex max-w-full items-center gap-2 rounded-[16px] bg-gray-100 px-2 py-1 text-sm text-gray-500 hover:bg-gray-200 transition-colors"
                  title={result.snippet || result.title}
                >
                  {faviconUrl ? (
                    <img src={faviconUrl} alt={result.title || ''} className="h-4 w-4 rounded-full bg-slate-100 shadow flex-shrink-0" onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }} />
                  ) : (
                    <Globe className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  )}
                  <span className="truncate flex-1">{result.title || resultUrl}</span>
                </a>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // No search results detected, render as normal markdown
  return (
    <div className="prose prose-sm max-w-none text-gray-800">
      <MarkdownRenderer content={content} />
    </div>
  );
}

// Clean tool call display - mimics the nice format in screenshots
function ToolCallDisplay({ tool }: { tool: { name: string; args: string; result?: string } }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse tool info to create user-friendly display
  const getToolDisplay = (): { icon: React.ReactNode; action: string; detail: string; type: string } => {
    const toolName = tool.name.toLowerCase();
    let args: Record<string, unknown> = {};
    try {
      args = JSON.parse(tool.args);
    } catch {
      // args might not be valid JSON
    }

    // Search tool
    if (toolName.includes('search') || toolName.includes('google')) {
      const query = args.query || args.search_query || args.q || '';
      return {
        icon: <Search className="w-4 h-4 text-blue-500" />,
        action: 'Searching for',
        detail: `"${query}"`,
        type: 'search'
      };
    }

    // Read/scrape webpage tool
    if (toolName.includes('scrape') || toolName.includes('read') || toolName.includes('fetch') || toolName.includes('browse')) {
      const url = args.url || args.webpage_url || args.link || '';
      return {
        icon: <Globe className="w-4 h-4 text-green-500" />,
        action: 'Reading',
        detail: String(url),
        type: 'read'
      };
    }

    // Code/Python tool
    if (toolName.includes('python') || toolName.includes('code') || toolName.includes('execute')) {
      return {
        icon: <Code className="w-4 h-4 text-purple-500" />,
        action: 'Running code',
        detail: '',
        type: 'code'
      };
    }

    // Reasoning tool
    if (toolName.includes('reason')) {
      return {
        icon: <Lightbulb className="w-4 h-4 text-yellow-500" />,
        action: 'Reasoning',
        detail: '',
        type: 'reasoning'
      };
    }

    // Default
    return {
      icon: <Wrench className="w-4 h-4 text-gray-500" />,
      action: tool.name,
      detail: '',
      type: 'default'
    };
  };

  const display = getToolDisplay();

  // Parse search results if available - check both tool type and result content
  const getSearchResults = () => {
    if (!tool.result) return null;
    try {
      const results = JSON.parse(tool.result);
      // Handle various result formats from different search APIs
      // Check if result looks like search results (has organic, organic_results, results, or array with link/url)
      if (results.organic && Array.isArray(results.organic)) {
        return results.organic.slice(0, 10);
      }
      if (results.organic_results && Array.isArray(results.organic_results)) {
        return results.organic_results.slice(0, 10);
      }
      if (results.results && Array.isArray(results.results)) {
        return results.results.slice(0, 10);
      }
      // Check if it's an array of items with link/url properties
      if (Array.isArray(results) && results.length > 0 && (results[0].link || results[0].url)) {
        return results.slice(0, 10);
      }
    } catch {
      // Not JSON results
    }
    return null;
  };

  const searchResults = getSearchResults();

  return (
    <div className="space-y-2">
      {/* Action line */}
      <div className="flex items-start gap-2">
        {display.icon}
        <div className="flex-1">
          <span className="text-gray-700">{display.action}</span>
          {display.detail && (
            <span className="text-gray-900 font-medium ml-1">
              {display.type === 'read' ? (
                <a href={display.detail} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  "{display.detail}"
                </a>
              ) : (
                display.detail
              )}
            </span>
          )}
        </div>
      </div>

      {/* Search results display - pill/chip style */}
      {searchResults && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <List className="w-4 h-4" />
            <span>Found {searchResults.length} results</span>
          </div>
          <div className="flex flex-col gap-2">
            {searchResults.map((result: { title?: string; link?: string; url?: string; favicon?: string; snippet?: string }, idx: number) => {
              const resultUrl = result.link || result.url || '';
              // Extract domain for favicon using Google's favicon service
              let faviconUrl = result.favicon;
              if (!faviconUrl && resultUrl) {
                try {
                  const domain = new URL(resultUrl).hostname;
                  faviconUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
                } catch {
                  // Invalid URL, use fallback
                }
              }
              return (
                <a
                  key={idx}
                  href={resultUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex max-w-full items-center gap-2 rounded-[16px] bg-gray-100 px-2 py-1 text-sm text-gray-500 hover:bg-gray-200 transition-colors"
                  title={result.snippet || result.title}
                >
                  {faviconUrl ? (
                    <img src={faviconUrl} alt={result.title || ''} className="h-4 w-4 rounded-full bg-slate-100 shadow flex-shrink-0" onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }} />
                  ) : (
                    <Globe className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  )}
                  <span className="truncate flex-1">{result.title || resultUrl}</span>
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* Expandable details for non-search, non-read tools with results */}
      {!searchResults && display.type !== 'read' && tool.result && (
        <div className="ml-6">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          >
            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <span>View result</span>
          </button>
          {isExpanded && (
            <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap text-gray-600">
              {tool.result.length > 1000 ? tool.result.slice(0, 1000) + '...' : tool.result}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

// LogItem for showing real-time logs - filter out internal spans
function LogItem({ log }: { log: Record<string, unknown> }) {
  const logType = (log.type as string) || '';
  const logName = (log.name as string) || '';
  const toolName = (log.tool_name as string) || '';
  const serverName = (log.server_name as string) || '';
  const input = log.input || log.arguments || log.args;

  // Filter out internal spans - these are noisy implementation details
  const internalPatterns = [
    'execute_tool_call',
    'create_message',
    'ToolManager',
    'SGLangClient',
    'MiroThinker',
    'IterativeAgent',
    '.run->',
    'OpenAI',
  ];

  const isInternalSpan = internalPatterns.some(pattern =>
    logName.includes(pattern) || toolName.includes(pattern)
  );

  // Skip internal spans and non-tool logs
  if (isInternalSpan) return null;
  if (logType === 'span_start' || logType === 'span_end') return null;
  if (logType === 'llm_call') return null;

  // Only show actual tool calls
  if (logType !== 'tool_call' && !toolName) return null;

  // Parse to create user-friendly display
  const getDisplay = (): { icon: React.ReactNode; text: string } => {
    const name = toolName.toLowerCase();
    let args: Record<string, unknown> = {};
    if (typeof input === 'object' && input !== null) {
      args = input as Record<string, unknown>;
    } else if (typeof input === 'string') {
      try { args = JSON.parse(input); } catch { /* ignore */ }
    }

    if (name.includes('search') || name.includes('google')) {
      const query = args.query || args.search_query || args.q || '';
      return { icon: <Search className="w-4 h-4 text-blue-500" />, text: `Searching for "${query}"` };
    }
    if (name.includes('scrape') || name.includes('read') || name.includes('fetch')) {
      const url = args.url || args.webpage_url || '';
      return { icon: <Globe className="w-4 h-4 text-green-500" />, text: `Reading ${url}` };
    }
    if (name.includes('python') || name.includes('code')) {
      return { icon: <Code className="w-4 h-4 text-purple-500" />, text: 'Running code...' };
    }
    if (name.includes('reason')) {
      return { icon: <Lightbulb className="w-4 h-4 text-yellow-500" />, text: 'Reasoning...' };
    }

    return { icon: <Wrench className="w-4 h-4 text-gray-500" />, text: serverName ? `${serverName} → ${toolName}` : toolName };
  };

  const display = getDisplay();

  return (
    <div className="flex items-center gap-2 text-sm text-gray-600">
      {display.icon}
      <span className="truncate">{display.text}</span>
    </div>
  );
}
