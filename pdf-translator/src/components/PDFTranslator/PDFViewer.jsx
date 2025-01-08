import { Upload } from 'lucide-react';
import { Card } from '../common/Card';
import {useRef} from "react";

export function PDFViewer({ file, currentPage, onPageChange }) {
  const fileInputRef = useRef(null);

  return (
    <Card className="flex-1">
      {file ? (
        <div className="relative min-h-[600px]">
          {/* PDF rendering logic here */}
        </div>
      ) : (
        <div
          className="flex flex-col items-center justify-center min-h-[600px] border-2 border-dashed border-gray-700 rounded-lg cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={48} className="text-gray-400 mb-4" />
          <p className="text-gray-400">Drop PDF here or click to upload</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => onFileSelect(e.target.files[0])}
            className="hidden"
          />
        </div>
      )}
    </Card>
  );
}