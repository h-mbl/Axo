export function TranslationPanel({ translationData, loading, error }) {
  const renderContent = () => {
    if (!translationData?.blocks) return 'Translation will appear here...';

    return (
      <div className="relative w-full">
        {translationData.blocks.map((block, index) => (
          <div
            key={index}
            className="relative mb-4" // Changed from absolute to relative for better layout
            style={block.bbox ? {
              left: `${block.bbox[0]}px`,
              top: `${block.bbox[1]}px`,
              width: `${block.bbox[2] - block.bbox[0]}px`,
            } : {}}
          >
            {block.type === 'text' && (
              <div className="whitespace-pre-wrap">{block.content}</div>
            )}
            {block.type === 'image' && (
              <div className="my-2">
                <img
                  src={block.content}
                  alt={block.caption || 'PDF image'}
                  className="max-w-full h-auto"
                />
                {block.caption && (
                  <p className="text-sm text-gray-600 mt-1">{block.caption}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

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
      ) : error ? (
        <div className="text-red-500 p-4">{error}</div>
      ) : (
        <div className="min-h-[600px] overflow-auto p-4">
          {renderContent()}
        </div>
      )}
    </Card>
  );
}