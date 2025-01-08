import { Download } from 'lucide-react';
import { Card } from '../common/Card';
import { Button } from '../common/Button';

export function TranslationPanel({ translation, loading, error }) {
  return (
    <Card className="flex-1">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Translation</h2>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>
      
      {loading ? (
        <div className="flex items-center justify-center min-h-[600px]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
        </div>
      ) : (
        <div className="min-h-[600px] whitespace-pre-wrap">
          {translation || 'Translation will appear here...'}
        </div>
      )}
    </Card>
  );
}
