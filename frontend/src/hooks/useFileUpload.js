import { useState, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';

export function useFileUpload(chatId) {
  const [error, setError] = useState(null);

  const uploadedFiles = useChatStore((s) => s.uploadedFiles);
  const setUploadedFile = useChatStore((s) => s.setUploadedFile);
  const clearUploadedFile = useChatStore((s) => s.clearUploadedFile);

  const file = uploadedFiles[chatId] ?? null;

  useEffect(() => {
    const timeout = setTimeout(() => {
      clearUploadedFile(chatId);
      setError(null);
    }, 0);

    return () => clearTimeout(timeout);
  }, [chatId, clearUploadedFile]);

  function onFileSelect(selectedFile) {
    if (selectedFile.type !== 'application/pdf') {
      setError('Only PDF files are supported.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File must be smaller than 10 MB.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    setUploadedFile(chatId, selectedFile);
    setError(null);
  }

  function clearFile() {
    clearUploadedFile(chatId);
    setError(null);
  }

  return { file, error, onFileSelect, clearFile };
}
