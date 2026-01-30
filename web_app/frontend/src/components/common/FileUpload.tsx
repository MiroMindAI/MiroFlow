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
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Upload File (Optional)
      </label>

      {uploadedFile ? (
        <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <File className="w-5 h-5 text-gray-500" />
            <span className="text-sm">{uploadedFile.file_name}</span>
            <span className="text-xs text-gray-500">({uploadedFile.file_type})</span>
          </div>
          <button
            onClick={handleRemove}
            className="p-1 hover:bg-gray-200 rounded"
            title="Remove file"
          >
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      ) : (
        <div
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
            isUploading
              ? 'border-blue-300 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".xlsx,.xls,.csv,.pdf,.doc,.docx,.txt,.json,.png,.jpg,.jpeg,.mp3,.wav,.mp4"
          />
          <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
          <p className="text-sm text-gray-600">
            {isUploading ? 'Uploading...' : 'Click to upload or drag and drop'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Excel, PDF, Word, Text, Images, Audio, Video
          </p>
        </div>
      )}

      {error && <p className="text-sm text-red-600 mt-1">{error}</p>}
    </div>
  );
}
