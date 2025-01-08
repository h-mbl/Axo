import { ChevronLeft, ChevronRight, FileText } from 'lucide-react';
import { Button } from '../common/Button';

export function Navigation({ currentPage, totalPages, onPageChange, onTranslate }) {
  return (
    <div className="mt-6 flex justify-center items-center gap-4">
      <Button
        variant="outline"
        size="icon"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>

      <span className="text-sm">
        Page {currentPage} of {totalPages}
      </span>

      <Button
        variant="outline"
        size="icon"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        <ChevronRight className="h-4 w-4" />
      </Button>

      <Button
        className="ml-4"
        onClick={onTranslate}
      >
        <FileText className="h-4 w-4 mr-2" />
        Translate
      </Button>
    </div>
  );
}