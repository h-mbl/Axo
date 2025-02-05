import React, { useState, useRef, useCallback } from 'react';
import { Upload, Settings, Download, Maximize2, Minimize2 } from 'lucide-react';
import { PdfViewer } from '@components/PDFTranslator/PdfViewer';

// Constants for panel dimensions and behavior
const PANEL_DEFAULTS = {
  MIN_WIDTH: 20,
  MAX_WIDTH: 80,
  DEFAULT_WIDTH: 50,
  COLLAPSED_WIDTH: 40,
};

const PDFTranslator = () => {
  // Panel layout state
  const [panelState, setPanelState] = useState({
    leftWidth: PANEL_DEFAULTS.DEFAULT_WIDTH,
    collapsed: { left: false, right: false },
  });

  // Translation state with clear structure
  const [translationState, setTranslationState] = useState({
    isTranslating: false,
    error: null,
    result: null
  });

  // Drag handling setup
  const dragRef = useRef({ isDragging: false, startX: 0, startWidth: 0 });

  // Panel resize handler with constraints
  const handlePanelResize = useCallback((e) => {
    if (!dragRef.current.isDragging) return;

    const delta = e.clientX - dragRef.current.startX;
    const containerWidth = document.querySelector('.main-container').offsetWidth;
    const newWidth = dragRef.current.startWidth + (delta / containerWidth) * 100;

    // Constrain width within acceptable range
    const constrainedWidth = Math.min(
      Math.max(PANEL_DEFAULTS.MIN_WIDTH, newWidth),
      PANEL_DEFAULTS.MAX_WIDTH
    );

    setPanelState(prev => ({
      ...prev,
      leftWidth: constrainedWidth,
      collapsed: {
        left: constrainedWidth <= PANEL_DEFAULTS.MIN_WIDTH,
        right: constrainedWidth >= PANEL_DEFAULTS.MAX_WIDTH
      }
    }));
  }, []);

  // Drag event handlers
  const startDrag = useCallback((e) => {
    dragRef.current = {
      isDragging: true,
      startX: e.clientX,
      startWidth: panelState.leftWidth,
    };

    document.addEventListener('mousemove', handlePanelResize);
    document.addEventListener('mouseup', stopDrag);
  }, [panelState.leftWidth, handlePanelResize]);

  const stopDrag = useCallback(() => {
    dragRef.current.isDragging = false;
    document.removeEventListener('mousemove', handlePanelResize);
    document.removeEventListener('mouseup', stopDrag);
  }, [handlePanelResize]);

  // Panel collapse/expand handler
  const togglePanel = useCallback((side) => {
    setPanelState(prev => {
      const newCollapsed = !prev.collapsed[side];
      const otherSide = side === 'left' ? 'right' : 'left';

      return {
        collapsed: {
          [side]: newCollapsed,
          [otherSide]: false
        },
        leftWidth: side === 'left'
          ? (newCollapsed ? 0 : PANEL_DEFAULTS.DEFAULT_WIDTH)
          : (newCollapsed ? 100 : PANEL_DEFAULTS.DEFAULT_WIDTH)
      };
    });
  }, []);

  // Translation result handler
  const handleTranslation = useCallback((response) => {
    setTranslationState({
      isTranslating: false,
      error: response.success ? null : response.message,
      result: response.success ? response : null
    });
  }, []);

  // Component for rendering translated blocks
  const renderBlock = (block, index) => {
    switch (block.type) {
      case 'text':
        return (
          <div
            key={index}
            className="text-block"
            style={{
              position: 'absolute',
              left: `${block.bbox[0]}px`,
              top: `${block.bbox[1]}px`,
              width: `${block.bbox[2] - block.bbox[0]}px`,
              fontSize: block.style.fontSize,
              fontFamily: block.style.fontFamily,
              fontWeight: block.style.fontWeight,
              textAlign: block.style.textAlign,
              lineHeight: block.style.lineHeight,
              transform: block.style.transform,
              color: `rgb(${(block.style.color >> 16) & 255}, ${(block.style.color >> 8) & 255}, ${block.style.color & 255})`,
               zIndex: 2
            }}
          >
            {block.content}
          </div>
        );
      case 'image':
        const getImageUrl = (path) => {
          const cleanPath = path.replace(/\\/g, '/');
          return `http://localhost:8001/output/${cleanPath.replace(/^output\//, '')}`;
        };

        // Utiliser les dimensions exactes du bbox pour le positionnement
        const imageStyles = {
          position: 'absolute',
          left: `${block.bbox[0]}px`,
          top: `${block.bbox[1]}px`,
          width: `${block.bbox[2] - block.bbox[0]}px`,
          height: `${block.bbox[3] - block.bbox[1]}px`,
          zIndex: 1
        };

        return (
          <div
            className="absolute"
            style={imageStyles}
          >
            <img
              src={getImageUrl(block.path)}
              alt=""
              className="w-full h-full object-contain"
              style={{
                display: 'block',  // Éviter les espaces blancs indésirables
                maxWidth: '100%',
                maxHeight: '100%'
              }}
              onError={(e) => {
                console.error('Erreur de chargement de l\'image:', {
                  originalPath: block.path,
                  url: e.target.src,
                  dimensions: {
                    containerWidth: block.bbox[2] - block.bbox[0],
                    containerHeight: block.bbox[3] - block.bbox[1],
                    naturalWidth: block.width,
                    naturalHeight: block.height
                  }
                });
                // Afficher un placeholder en cas d'erreur
                e.target.style.display = 'none';
                e.target.parentElement.classList.add('bg-gray-100');
                e.target.parentElement.innerHTML = 'Image non disponible';
              }}
              onLoad={(e) => {
                console.log('Image chargée avec succès:', {
                  path: block.path,
                  naturalSize: {
                    width: e.target.naturalWidth,
                    height: e.target.naturalHeight
                  },
                  containerSize: {
                    width: block.bbox[2] - block.bbox[0],
                    height: block.bbox[3] - block.bbox[1]
                  }
                });
              }}
            />
          </div>
        );
      default:
        return null;
    }
  };

  // Translation content display component
  const TranslatedContent = () => {
    const { isTranslating, error, result } = translationState;

    if (isTranslating) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      );
    }

    if (error) {
      return <div className="text-red-500 p-4">{error}</div>;
    }

    if (!result) {
      return (
        <div className="text-gray-500 p-4">
          Upload a PDF and click translate to see the translation here...
        </div>
      );
    }

     return (
    <div className="h-full overflow-auto">
      {/* Content container that maintains the PDF dimensions */}
      <div
        className="relative min-h-full"
        style={{
          width: result.page_dimensions.width,
          minHeight: result.page_dimensions.height,
          transform: `rotate(${result.page_dimensions.rotation}deg)`,
          transformOrigin: 'top left'
        }}
      >
        {/* Blocks container to preserve positioning context */}
        <div className="absolute top-0 left-0 w-full h-full">
          {result.blocks.map((block, index) => renderBlock(block, index))}
        </div>
      </div>
    </div>
  );
};

  // Main layout
  return (
    <div className="min-h-screen bg-white text-gray-800">
      <Header />

      <div className="main-container flex h-[calc(100vh-4rem)] relative">
        {/* Left panel with PDF viewer */}
        <Panel
          side="left"
          width={panelState.leftWidth}
          isCollapsed={panelState.collapsed.left}
          isOtherCollapsed={panelState.collapsed.right}
          onToggle={() => togglePanel('left')}
          onDragStart={startDrag}
        >
          <PdfViewer onTranslate={handleTranslation} />
        </Panel>

        {/* Right panel with translation */}
        {!panelState.collapsed.right && (
          <Panel
            side="right"
            width={100 - panelState.leftWidth}
            isCollapsed={panelState.collapsed.right}
            onToggle={() => togglePanel('right')}
          >
            <TranslationPanel result={translationState.result}>
              <TranslatedContent />
            </TranslationPanel>
          </Panel>
        )}
      </div>
    </div>
  );
};

// Header component with language selection
const Header = () => (
  <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
    <h1 className="text-xl font-semibold">PDF Translator</h1>
    <div className="flex items-center space-x-4">
      <select className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
        <option>Portuguese</option>
        <option>French</option>
        <option>Spanish</option>
      </select>
      <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
        <Settings className="w-5 h-5"/>
      </button>
    </div>
  </header>
);

// Resizable panel component
const Panel = ({ side, width, isCollapsed, isOtherCollapsed, onToggle, onDragStart, children }) => {
  const effectiveWidth = isCollapsed
    ? `${PANEL_DEFAULTS.COLLAPSED_WIDTH}px`
    : isOtherCollapsed
      ? '100%'
      : `${width}%`;

  return (
    <div
      className="transition-all duration-300 relative"
      style={{
        width: effectiveWidth,
        minWidth: isCollapsed ? `${PANEL_DEFAULTS.COLLAPSED_WIDTH}px` : '0',
        maxWidth: isOtherCollapsed ? '100%' : `${width}%`,
      }}
    >
      <div className="h-full p-6 relative">
        <div className={`h-full border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 ${
          isCollapsed ? 'opacity-0 pointer-events-none' : ''
        }`}>
          {children}
        </div>
        <button
          className="absolute top-4 right-4 p-2 bg-white rounded-full shadow-lg transition-opacity z-10"
          onClick={onToggle}
        >
          {isCollapsed ? <Maximize2 className="w-4 h-4"/> : <Minimize2 className="w-4 h-4"/>}
        </button>
        {onDragStart && !isCollapsed && (
          <div
            className="absolute right-0 top-0 w-4 h-full cursor-col-resize hover:bg-blue-100 transition-colors"
            onMouseDown={onDragStart}
          />
        )}
      </div>
    </div>
  );
};

// Translation panel component
const TranslationPanel = ({ result, children }) => (
  <div className="h-full bg-white rounded-lg shadow flex flex-col"> {/* Add flex column */}
    <div className="flex-none p-4 border-b"> {/* Header becomes flex-none */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium">Translation</h2>
        {result?.success && (
          <button className="flex items-center space-x-2 text-gray-600 hover:text-gray-800">
            <Download className="w-4 h-4"/>
            <span>Export</span>
          </button>
        )}
      </div>
    </div>
    <div className="flex-1 overflow-hidden p-4"> {/* Content area becomes flex-1 with overflow hidden */}
      {children}
    </div>
  </div>
);
export default PDFTranslator;