import React, { useState, useRef } from 'react';
import { Upload, Settings, Download, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';
import PdfViewer from "./PdfViewer";

const PDFTranslator = () => {
  const [leftPanelWidth, setLeftPanelWidth] = useState(50); // en pourcentage
  const [isPanelCollapsed, setIsPanelCollapsed] = useState({ left: false, right: false });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const handleDragStart = (e) => {
    setIsDragging(true);
    dragStartX.current = e.clientX;
    dragStartWidth.current = leftPanelWidth;
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('mouseup', handleDragEnd);
  };

  const handleDrag = (e) => {
    if (!isDragging) return;
    const delta = e.clientX - dragStartX.current;
    const containerWidth = document.querySelector('.main-container').offsetWidth;
    const newWidth = (dragStartWidth.current + (delta / containerWidth) * 100);
    setLeftPanelWidth(Math.min(Math.max(20, newWidth), 80));
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('mouseup', handleDragEnd);
  };
  const handlePanelToggle = (side) => {
  const newCollapsed = !isPanelCollapsed[side];

  if (side === 'left') {
    // Si on collapse le panneau gauche, il prend 0% de largeur
    // Si on le restaure, on revient à l'état de base de 50%
    setLeftPanelWidth(newCollapsed ? 0 : 50);
    setIsPanelCollapsed({
      ...isPanelCollapsed,
      left: newCollapsed,
      right: false  // On s'assure que le panneau droit est visible
    });
  } else if (side === 'right') {
    // Si on collapse le panneau droit, le panneau gauche prend 100%
    // Si on le restaure, on revient à l'état de base de 50%
    setLeftPanelWidth(newCollapsed ? 100 : 50);
    setIsPanelCollapsed({
      ...isPanelCollapsed,
      right: newCollapsed,
      left: false  // On s'assure que le panneau gauche est visible
    });
  }
};

  return (
      <div className="min-h-screen bg-white text-gray-800">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">PDF Translator</h1>
          <div className="flex items-center space-x-4">
            <select
                className="bg-gray-100 border border-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option>Portuguese</option>
              <option>French</option>
              <option>Spanish</option>
            </select>
            <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
              <Settings className="w-5 h-5"/>
            </button>
          </div>
        </header>

        {/* Main Content */}
        <div className="main-container flex h-[calc(100vh-4rem)] relative">
          {/* Left Panel */}
          <div
              className="transition-all duration-300 relative"
              style={{
                width: isPanelCollapsed.left
                    ? '40px'
                    : isPanelCollapsed.right
                        ? '100%'
                        : `${leftPanelWidth}%`,
              }}
          >
            <div className="h-full p-6 relative group">
              <div
                  className={`h-full border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center bg-gray-50 ${
                      isPanelCollapsed.left ? 'opacity-0' : ''
                  }`}
              >
                <div className="text-center">
                  {/* Ajout du composant PdfViewer */}
                  <PdfViewer/>
                </div>
              </div>
              <button
                  className="absolute top-4 right-4 p-2 bg-white rounded-full shadow-lg transition-opacity"
                  onClick={() => handlePanelToggle('left')}
              >
                {isPanelCollapsed.left ? (
                    <Maximize2 className="w-4 h-4"/>
                ) : (
                    <Minimize2 className="w-4 h-4"/>
                )}
              </button>
            </div>
          </div>

          {/* Right Panel */}
          {!isPanelCollapsed.right && (
              <div
                  className="transition-all duration-300 relative"
                  style={{
                    width: `${100 - leftPanelWidth}%`,
                  }}
              >
                <div className="h-full p-6 relative group">
                  <div className="h-full border border-gray-200 rounded-lg bg-white p-4">
                    <div className="flex justify-between items-center mb-4">
                      <h2 className="text-lg font-medium">Translation</h2>
                      <button className="flex items-center space-x-2 text-gray-600 hover:text-gray-800">
                        <Download className="w-4 h-4"/>
                        <span>Export</span>
                      </button>
                    </div>
                    <p className="text-gray-500">Translated content would appear here...</p>
                  </div>
                  <button
                      className="absolute top-4 right-4 p-2 bg-white rounded-full shadow-lg"
                      onClick={() => handlePanelToggle('right')}
                  >
                    <Minimize2 className="w-4 h-4"/>
                  </button>
                </div>
              </div>
          )}
        </div>


        {/* Footer Navigation
        <div
            className="fixed bottom-6 left-1/2 transform -translate-x-1/2 flex items-center space-x-4 bg-white shadow-lg rounded-full px-4 py-2">
          <button className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50">
            <ChevronLeft className="w-4 h-4"/>
          </button>
          <span className="text-sm">Page 1 of 1</span>
          <button className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50">
            <ChevronRight className="w-4 h-4"/>
          </button>
          <button className="ml-2 bg-blue-500 text-white px-4 py-2 rounded-full hover:bg-blue-600 transition-colors">
            Translate
          </button>
        </div> */}
      </div>
  );
};

export default PDFTranslator;