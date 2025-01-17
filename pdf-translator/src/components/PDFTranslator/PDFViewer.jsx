import React, { useState, useEffect, useCallback, useRef } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
import {
  Upload,
  Download,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Settings,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { translationService } from '../../services/translationService';

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


  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedContent, setTranslatedContent] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [selectedLanguages, setSelectedLanguages] = useState({
    source: 'auto',
    target: 'fr'
  });
   const handleTranslationComplete = (result) => {
        setTranslatedContent(result);
    };



  // Références
  const containerRef = useRef(null);
  const fileInputRef = useRef(null);

  // Fonction pour calculer l'échelle optimale
  const calculateOptimalScale = useCallback((page) => {
    if (!containerRef.current) return 1.0;

    const containerWidth = containerRef.current.clientWidth - 48;
    const viewport = page.getViewport({ scale: 1.0, rotation });
    return containerWidth / viewport.width;
  }, [rotation]);

  // Fonction pour rendre une page
  const renderPage = useCallback(async (page) => {
    try {
      const optimalScale = calculateOptimalScale(page);
      const viewport = page.getViewport({ scale: scale * optimalScale, rotation });

      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page.render({
        canvasContext: context,
        viewport
      }).promise;

      setCurrentPageImage(canvas.toDataURL());
    } catch (error) {
      setErrorMessage('Erreur lors du rendu de la page : ' + error.message);
      throw error;
    }
  }, [scale, rotation, calculateOptimalScale]);

  // Fonction pour charger un fichier PDF
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsLoading(true);
      setErrorMessage('');
      setTranslatedContent(''); // Réinitialiser la traduction lors du chargement d'un nouveau fichier
      setPdfFile(file); // Sauvegarder le fichier pour la traduction

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

          const firstPage = await loadedPdf.getPage(1);
          await renderPage(firstPage);
        } catch (error) {
          setErrorMessage('Erreur lors du chargement du PDF : ' + error.message);
        } finally {
          setIsLoading(false);
        }
      };

      fileReader.readAsArrayBuffer(file);
    } catch (error) {
      setErrorMessage('Erreur lors de la lecture du fichier : ' + error.message);
      setIsLoading(false);
    }
  };

  // Fonction pour changer de page
  const changePage = useCallback(async (newPage) => {
    if (!pdfDocument || newPage < 1 || newPage > totalPages) return;

    try {
      setIsLoading(true);
      const page = await pdfDocument.getPage(newPage);
      await renderPage(page);
      setCurrentPage(newPage);
    } catch (error) {
      setErrorMessage('Erreur lors du changement de page');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, [pdfDocument, totalPages, renderPage]);

  // Fonction pour gérer le zoom
  const handleZoom = useCallback((delta) => {
    setScale(prevScale => {
      const newScale = prevScale + delta;
      return newScale >= 0.25 && newScale <= 3 ? newScale : prevScale;
    });
  }, []);

  // Fonction pour gérer la rotation
  const handleRotate = useCallback(() => {
    setRotation(prev => (prev + 90) % 360);
  }, []);

  // Fonction pour gérer la traduction
  const handleTranslate = async () => {
    if (!pdfFile || isTranslating) return;

    try {
        setIsTranslating(true);
        setErrorMessage('');

        const result = await translationService.translatePdfPage(
            pdfFile,
            currentPage,
            selectedLanguages.source,
            selectedLanguages.target
        );

        if (result.success) {
            // Nous n'avons plus besoin de gérer translatedContent ici
            // car c'est le composant parent qui s'en charge
            console.log('Résultat de la traduction:', result);
            return result;
        } else {
            throw new Error(result.error || 'Échec de la traduction');
        }
    } catch (error) {
        setErrorMessage('Erreur lors de la traduction : ' + error.message);
        console.error('Erreur de traduction:', error);
    } finally {
        setIsTranslating(false);
    }
};


  // Effect pour mettre à jour la page quand le scale ou la rotation change
  useEffect(() => {
    if (pdfDocument) {
      pdfDocument.getPage(currentPage).then(renderPage).catch(console.error);
    }
  }, [pdfDocument, currentPage, scale, rotation, renderPage]);

  return (
    <div className="flex flex-col h-full relative bg-white">
      {/* Barre d'outils supérieure */}
      <div className="flex justify-between items-center p-4 border-b">
        <div className="flex items-center space-x-4">
          <label className="cursor-pointer bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg px-4 py-2 transition-colors">
            <input
              ref={fileInputRef}
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
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                title="Zoom arrière"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-sm font-medium min-w-[60px] text-center">
                {Math.round(scale * 100)}%
              </span>
              <button
                onClick={() => handleZoom(0.1)}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                title="Zoom avant"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                onClick={handleRotate}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                title="Pivoter"
              >
                <RotateCw className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Zone de visualisation du PDF */}
      <div
        ref={containerRef}
        className="flex-grow overflow-auto relative p-6"
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

       {/* Barre de navigation et traduction avec état de chargement */}
      {pdfDocument && (
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 flex items-center space-x-4 bg-white shadow-lg rounded-full px-4 py-2 z-10">
          <button
            className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50 transition-colors"
            onClick={() => changePage(currentPage - 1)}
            disabled={currentPage <= 1 || isLoading}
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="text-sm font-medium min-w-[100px] text-center">
            Page {currentPage} sur {totalPages}
          </span>

          <button
            className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50 transition-colors"
            onClick={() => changePage(currentPage + 1)}
            disabled={currentPage >= totalPages || isLoading}
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          <button
            onClick={handleTranslate}
            disabled={isTranslating || isLoading || !pdfFile}
            className={`ml-2 px-4 py-2 rounded-full transition-colors ${
              isTranslating 
                ? 'bg-blue-400 cursor-wait' 
                : 'bg-blue-500 hover:bg-blue-600'
            } text-white disabled:opacity-50`}
          >
            {isTranslating ? 'Traduction en cours...' : 'Traduire'}
          </button>
        </div>
      )}

      {/* Message d'erreur */}
      {errorMessage && (
        <div className="absolute bottom-24 left-1/2 transform -translate-x-1/2 bg-red-100 text-red-600 px-4 py-2 rounded-lg">
          {errorMessage}
        </div>
      )}
    </div>
  );
};


export default PdfViewer;