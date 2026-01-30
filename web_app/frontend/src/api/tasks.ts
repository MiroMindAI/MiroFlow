import { apiClient } from './client';
import type {
  Task,
  TaskCreate,
  TaskListResponse,
  TaskStatusUpdate,
  ConfigListResponse,
  UploadResponse,
} from '../types/task';

export async function createTask(data: TaskCreate): Promise<Task> {
  const response = await apiClient.post<Task>('/api/tasks', data);
  return response.data;
}

export async function listTasks(page = 1, pageSize = 20): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>('/api/tasks', {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function getTask(taskId: string): Promise<Task> {
  const response = await apiClient.get<Task>(`/api/tasks/${taskId}`);
  return response.data;
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusUpdate> {
  const response = await apiClient.get<TaskStatusUpdate>(`/api/tasks/${taskId}/status`);
  return response.data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/api/tasks/${taskId}`);
}

export async function listConfigs(): Promise<ConfigListResponse> {
  const response = await apiClient.get<ConfigListResponse>('/api/configs');
  return response.data;
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<UploadResponse>('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}
