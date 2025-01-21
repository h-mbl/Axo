import React, { useState, useRef, useCallback } from 'react';
import { Upload, Settings, Download, Maximize2, Minimize2 } from 'lucide-react';
import PdfViewer from "./PdfViewer";

// Constantes pour améliorer la maintenabilité
const PANEL_DEFAULTS = {
  MIN_WIDTH: 20,
  MAX_WIDTH: 80,
  DEFAULT_WIDTH: 50,
  COLLAPSED_LEFT_WIDTH: 40,
};

const PDFTranslator = () => {
  // États principaux
  const [panelState, setPanelState] = useState({
    leftWidth: PANEL_DEFAULTS.DEFAULT_WIDTH,
    collapsed: { left: false, right: false },
  });

  // États de traduction
  const [translationState, setTranslationState] = useState({
    content: null,
    isTranslating: false,
    error: null,
    result: null,
  });

  // États pour le drag and drop
  const dragRef = useRef({ isDragging: false, startX: 0, startWidth: 0 });

  // Gestionnaire de redimensionnement des panneaux
  const handlePanelResize = useCallback((e) => {
  if (!dragRef.current.isDragging) return;

  const delta = e.clientX - dragRef.current.startX;
  const containerWidth = document.querySelector('.main-container').offsetWidth;
  const newWidth = dragRef.current.startWidth + (delta / containerWidth) * 100;

  // Assurez-vous que la largeur reste dans les limites acceptables
  const constrainedWidth = Math.min(Math.max(0, newWidth), 100);

  setPanelState(prev => ({
    ...prev,
    leftWidth: constrainedWidth,
    collapsed: {
      left: constrainedWidth === 0,
      right: constrainedWidth === 100
    }
  }));
  }, []);

  // Gestionnaires d'événements pour le drag
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

  // Gestion du basculement des panneaux
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

  // Gestion de la traduction
  const handleTranslation = useCallback((result) => {
    setTranslationState(prev => ({
      ...prev,
      result,
      isTranslating: false,
      content: result.success ? {
        text: result.translated_text,
        htmlPath: result.html_path,
      } : null,
      error: result.success ? null : (result.message || 'Translation failed'),
    }));
  }, []);

  // Composant pour le contenu traduit
  const TranslatedContent = () => {
    const { isTranslating, error, content } = translationState;

    if (isTranslating) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      );
    }

    if (error) return <div className="text-red-500 p-4">{error}</div>;
    if (!content) return <p className="text-gray-500">Upload a PDF and click translate to see the translation here...</p>;

    return (
      <div className="h-full overflow-auto">
        {content.htmlPath ? (
          <iframe src={content.htmlPath} className="w-full h-full border-0" title="Translated content" />
        ) : (
          <div className="whitespace-pre-wrap">{content.text}</div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-white text-gray-800">
      <Header />

      <div className="main-container flex h-[calc(100vh-4rem)] relative">
        {/* Panneau gauche */}
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

        {/* Panneau droit */}
        {!panelState.collapsed.right && (
          <Panel
            side="right"
            width={100 - panelState.leftWidth}
            isCollapsed={panelState.collapsed.right}
            onToggle={() => togglePanel('right')}
          >
            <TranslationPanel
              translatedResult={translationState.result}
              children={<TranslatedContent />}
            />
          </Panel>
        )}
      </div>
    </div>
  );
};

// Composants auxiliaires
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

const Panel = ({ side, width, isCollapsed, isOtherCollapsed, onToggle, onDragStart, children }) => {
  // Calculer la largeur effective du panneau en fonction des états
  const getEffectiveWidth = () => {
    if (isCollapsed) {
      return '40px'; // Largeur minimale fixe quand le panneau est collapsé
    }
    if (isOtherCollapsed) {
      return '100%'; // Largeur maximale quand l'autre panneau est collapsé
    }
    return `${width}%`;
  };

  return (
    <div
      className="transition-all duration-300 relative"
      style={{
        width: getEffectiveWidth(),
        minWidth: isCollapsed ? '40px' : '0',
        maxWidth: isOtherCollapsed ? '100%' : `${width}%`,
      }}
    >
      <div className="h-full p-6 relative group">
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


const TranslationPanel = ({ translatedResult, children }) => (
  <div className="h-full border border-gray-200 rounded-lg bg-white p-4">
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-lg font-medium">Translation</h2>
      {translatedResult && (
        <button className="flex items-center space-x-2 text-gray-600 hover:text-gray-800">
          <Download className="w-4 h-4"/>
          <span>Export</span>
        </button>
      )}
    </div>
    <div className="h-full overflow-auto">
      {children}
    </div>
  </div>
);

export default PDFTranslator;