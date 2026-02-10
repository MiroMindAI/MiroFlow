import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Send } from 'lucide-react';
import { createTask, listConfigs } from '../../api/tasks';
import FileUpload from '../common/FileUpload';
import type { UploadResponse } from '../../types/task';

interface TaskFormProps {
  onTaskCreated: (taskId: string) => void;
}

export default function TaskForm({ onTaskCreated }: TaskFormProps) {
  const [description, setDescription] = useState('');
  const [configPath, setConfigPath] = useState('');
  const [uploadedFile, setUploadedFile] = useState<UploadResponse | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { data: configData } = useQuery({
    queryKey: ['configs'],
    queryFn: listConfigs,
  });

  // Set default config when loaded
  if (configData && !configPath) {
    setConfigPath(configData.default);
  }

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: (task) => {
      onTaskCreated(task.id);
      setDescription('');
      setUploadedFile(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;

    createMutation.mutate({
      task_description: description,
      config_path: configPath || configData?.default || 'config/agent_web_demo.yaml',
      file_id: uploadedFile?.file_id,
    });
  };

  const examples = [
    'What is the capital of France?',
    'Explain quantum computing in simple terms',
    'What are the latest developments in AI research?',
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Question</label>
        <div className="relative">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter your question..."
            rows={4}
            className="w-full px-3 py-2 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
          <div className="absolute bottom-2 right-2">
            <FileUpload onFileUploaded={setUploadedFile} uploadedFile={uploadedFile} />
          </div>
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-gray-600 hover:text-gray-800"
        >
          {showAdvanced ? '- Hide' : '+ Show'} Advanced Settings
        </button>

        {showAdvanced && (
          <div className="mt-2 p-3 bg-gray-50 rounded-lg">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Agent Configuration
            </label>
            <select
              value={configPath}
              onChange={(e) => setConfigPath(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white"
            >
              {configData?.configs.map((config) => (
                <option key={config} value={config}>
                  {config}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <button
        type="submit"
        disabled={!description.trim() || createMutation.isPending}
        className="w-full py-2.5 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
      >
        <Send className="w-4 h-4" />
        <span>{createMutation.isPending ? 'Submitting...' : 'Submit'}</span>
      </button>

      {createMutation.error && (
        <div className="text-red-600 text-sm p-2 bg-red-50 rounded">
          Error: {(createMutation.error as Error).message}
        </div>
      )}

      <div className="pt-2">
        <p className="text-xs text-gray-500 mb-2">Example questions:</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setDescription(example)}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 transition-colors"
            >
              {example.length > 30 ? example.slice(0, 30) + '...' : example}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}
