import React, { useState, useRef } from 'react';
import { PDFViewer } from './PDFViewer';
import { TranslationPanel } from './TranslationPanel';
import { Header } from './Header';
import { Navigation } from './Navigation';
import { useTranslation } from '../../hooks/useTranslation';

export function PDFTranslator() {
  const [currentFile, setCurrentFile] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { translation, loading, error, translateContent } = useTranslation();

  return (
    <div className="p-6">
      <Header
        currentFile={currentFile}
        onFileSelect={setCurrentFile}
      />

      <main className="flex gap-6 mt-6">
        <PDFViewer
          file={currentFile}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
        <TranslationPanel
          translation={translation}
          loading={loading}
          error={error}
        />
      </main>

      <Navigation
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
        onTranslate={() => translateContent(currentFile, currentPage)}
      />
    </div>
  );
}