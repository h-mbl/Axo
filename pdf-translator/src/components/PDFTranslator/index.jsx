// index.jsx
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
      setLeftPanelWidth(newCollapsed ? 0 : 50);
      setIsPanelCollapsed({
        ...isPanelCollapsed,
        left: newCollapsed,
        right: false
      });
    } else if (side === 'right') {
      setLeftPanelWidth(newCollapsed ? 100 : 50);
      setIsPanelCollapsed({
        ...isPanelCollapsed,
        right: newCollapsed,
        left: false
      });
    }
  };

  return (
      <div className="min-h-screen bg-gradient-to-r from-gray-50 via-white to-gray-100 text-gray-800">
        {/* Header */}
        <header className="bg-white shadow-md px-6 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">PDF Translator</h1>
          <div className="flex items-center space-x-4">
            <select
                className="bg-gray-100 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option>Portuguese</option>
              <option>French</option>
              <option>Spanish</option>
            </select>
            <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
              <Settings className="w-5 h-5 text-gray-500"/>
            </button>
          </div>
        </header>

        {/* Main Content */}
        <div className="main-container flex h-[calc(100vh-4rem)] relative">
          {/* Left Panel */}
          <div
              className="transition-all duration-300 relative shadow-lg bg-white"
              style={{
                width: isPanelCollapsed.left
                    ? '40px'
                    : isPanelCollapsed.right
                        ? '100%'
                        : `${leftPanelWidth}%`,
              }}
          >
            <div className="h-full p-6 relative">
              <div
                  className={`h-full border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center bg-gray-50 $ {
                      isPanelCollapsed.left ? 'opacity-0' : ''
                  }`}
              >
                <div className="text-center">
                  <PdfViewer/>
                </div>
              </div>
              <button
                  className="absolute top-4 right-4 p-2 bg-blue-500 text-white rounded-full shadow-lg transition-opacity hover:bg-blue-600"
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
                  className="transition-all duration-300 relative bg-white shadow-lg"
                  style={{
                    width: `${100 - leftPanelWidth}%`,
                  }}
              >
                <div className="h-full p-6 relative">
                  <div className="h-full border border-gray-200 rounded-lg bg-gray-50 p-4">
                    <div className="flex justify-between items-center mb-4">
                      <h2 className="text-lg font-medium">Translation</h2>
                      <button className="flex items-center space-x-2 text-gray-600 hover:text-gray-800">
                        <Download className="w-4 h-4"/>
                        <span>Export</span>
                      </button>
                    </div>
                    <p className="text-gray-500">Translated content will appear here...</p>
                  </div>
                  <button
                      className="absolute top-4 right-4 p-2 bg-blue-500 text-white rounded-full shadow-lg hover:bg-blue-600"
                      onClick={() => handlePanelToggle('right')}
                  >
                    <Minimize2 className="w-4 h-4"/>
                  </button>
                </div>
              </div>
          )}
        </div>
      </div>
  );
};

export default PDFTranslator;
