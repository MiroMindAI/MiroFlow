export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface FileInfo {
  file_id: string;
  file_name: string;
  file_type: string;
  absolute_file_path: string;
}

export interface Task {
  id: string;
  task_description: string;
  config_path: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  current_turn: number;
  max_turns: number;
  step_count: number;
  final_answer: string | null;
  summary: string | null;
  error_message: string | null;
  file_info: FileInfo | null;
  log_path: string | null;
}

export interface TaskCreate {
  task_description: string;
  config_path: string;
  file_id?: string;
}

export interface Message {
  role: string;
  content: string;
}

export interface TaskStatusUpdate {
  id: string;
  status: TaskStatus;
  current_turn: number;
  step_count: number;
  recent_logs: unknown[];
  messages: Message[];
  final_answer: string | null;
  summary: string | null;
  error_message: string | null;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConfigListResponse {
  configs: string[];
  default: string;
}

export interface UploadResponse {
  file_id: string;
  file_name: string;
  file_type: string;
  absolute_file_path: string;
}
