import { useState, useRef } from 'react';
import { Upload, X, File } from 'lucide-react';
import { uploadFile } from '../../api/tasks';
import type { UploadResponse } from '../../types/task';

interface FileUploadProps {
  onFileUploaded: (file: UploadResponse | null) => void;
  uploadedFile: UploadResponse | null;
}

export default function FileUpload({ onFileUploaded, uploadedFile }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadFile(file);
      onFileUploaded(result);
    } catch (err) {
      setError((err as Error).message || 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = () => {
    onFileUploaded(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
        accept=".xlsx,.xls,.csv,.pdf,.doc,.docx,.txt,.json,.png,.jpg,.jpeg,.mp3,.wav,.mp4"
      />

      {uploadedFile ? (
        <div className="flex items-center gap-1 bg-white border border-gray-300 rounded px-2 py-1">
          <File className="w-4 h-4 text-gray-500" />
          <span className="text-xs max-w-[100px] truncate">{uploadedFile.file_name}</span>
          <button
            onClick={handleRemove}
            className="p-0.5 hover:bg-gray-200 rounded"
            title="Remove file"
          >
            <X className="w-3 h-3 text-gray-500" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
          className={`p-2 rounded-lg transition-colors ${
            isUploading
              ? 'bg-blue-100 text-blue-600'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
          }`}
          title="Upload file"
        >
          <Upload className="w-5 h-5" />
        </button>
      )}

      {error && (
        <div className="absolute bottom-full right-0 mb-1 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
          {error}
        </div>
      )}
    </div>
  );
}
