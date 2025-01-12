import React, { useState, useEffect, useCallback, useRef } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
import { Upload, Download, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';

// Configuration du worker PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/legacy/build/pdf.worker.mjs';

const PdfViewer = () => {
  // États pour la gestion du PDF
  const [pdfDocument, setPdfDocument] = useState(null);
  const [currentPageImage, setCurrentPageImage] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Références pour les mesures et le conteneur
  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  // Fonction pour calculer l'échelle optimale en fonction de la largeur du conteneur
  const calculateOptimalScale = useCallback((page) => {
    if (!containerRef.current) return 1.0;

    const containerWidth = containerRef.current.clientWidth - 48; // Soustrait le padding
    const viewport = page.getViewport({ scale: 1.0, rotation });
    return containerWidth / viewport.width;
  }, [rotation]);

  // Fonction pour rendre une page du PDF
  const renderPage = useCallback(async (pageNumber) => {
    if (!pdfDocument) return;

    try {
      setIsLoading(true);
      const page = await pdfDocument.getPage(pageNumber);

      // Calculer l'échelle optimale
      const optimalScale = calculateOptimalScale(page);
      const viewport = page.getViewport({ scale: scale * optimalScale, rotation });

      // Configurer le canvas
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      // Rendre la page
      await page.render({
        canvasContext: context,
        viewport
      }).promise;

      setCurrentPageImage(canvas.toDataURL());
      setIsLoading(false);
    } catch (error) {
      setErrorMessage('Erreur lors du rendu de la page : ' + error.message);
      setIsLoading(false);
    }
  }, [pdfDocument, scale, rotation, calculateOptimalScale]);

  // Gestionnaire pour le chargement du PDF
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsLoading(true);
      setErrorMessage('');

      const fileReader = new FileReader();
      fileReader.onload = async (e) => {
        try {
          const typedArray = new Uint8Array(e.target.result);
          const loadedPdf = await pdfjs.getDocument(typedArray).promise;

          setPdfDocument(loadedPdf);
          setTotalPages(loadedPdf.numPages);
          setCurrentPage(1);
          setScale(1.0);
          setRotation(0);
        } catch (error) {
          setErrorMessage('Erreur lors du chargement du PDF : ' + error.message);
        }
        setIsLoading(false);
      };

      fileReader.readAsArrayBuffer(file);
    } catch (error) {
      setErrorMessage('Erreur lors de la lecture du fichier : ' + error.message);
      setIsLoading(false);
    }
  };

  // Fonctions de navigation et de contrôle
  const changePage = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleZoom = (delta) => {
    setScale(prevScale => {
      const newScale = prevScale + delta;
      return newScale >= 0.25 && newScale <= 3 ? newScale : prevScale;
    });
  };

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360);
  };

  // Effet pour rendre la page courante quand nécessaire
  useEffect(() => {
    if (pdfDocument) {
      renderPage(currentPage);
    }
  }, [pdfDocument, currentPage, scale, rotation, renderPage]);

  return (
    <div className="flex flex-col h-full">
      {/* Barre d'outils supérieure */}
      <div className="flex justify-between items-center p-4 border-b">
        <div className="flex items-center space-x-4">
          <label className="cursor-pointer bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg px-4 py-2 transition-colors">
            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Upload className="w-5 h-5 inline-block mr-2" />
            Charger un PDF
          </label>

          {pdfDocument && (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleZoom(-0.1)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-sm">{Math.round(scale * 100)}%</span>
              <button
                onClick={() => handleZoom(0.1)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleRotate}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <RotateCw className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Message d'erreur */}
      {errorMessage && (
        <div className="text-red-500 p-4 text-center">{errorMessage}</div>
      )}

      {/* Conteneur principal du PDF */}
      <div
        ref={containerRef}
        className="flex-grow overflow-auto relative bg-gray-50 p-6"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
          </div>
        ) : currentPageImage ? (
          <div className="flex justify-center">
            <img
              src={currentPageImage}
              alt={`Page ${currentPage}`}
              className="max-w-full shadow-lg"
              style={{
                transform: `rotate(${rotation}deg)`,
                transition: 'transform 0.3s ease'
              }}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Aucun PDF chargé
          </div>
        )}
      </div>

      {/* Barre de navigation */}
      {pdfDocument && (
        <div className="flex items-center justify-center space-x-4 p-4 border-t bg-white">
          <button
            className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
            onClick={() => changePage(currentPage - 1)}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="text-sm">
            Page {currentPage} sur {totalPages}
          </span>

          <button
            className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
            onClick={() => changePage(currentPage + 1)}
            disabled={currentPage >= totalPages}
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default PdfViewer;