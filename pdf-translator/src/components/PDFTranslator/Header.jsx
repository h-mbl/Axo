import { LanguageSelector } from '../common/LanguageSelector';
import { Settings } from 'lucide-react';
import { Button } from '../common/Button';

export function Header({ currentFile, onFileSelect }) {
  return (
    <header className="flex justify-between items-center">
      <h1 className="text-2xl font-bold">Axo</h1>
      <div className="flex gap-4">
        <LanguageSelector />
        <Button variant="icon">
          <Settings className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}