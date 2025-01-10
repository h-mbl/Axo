import React, { useState } from "react";
import * as pdfjs from "pdfjs-dist/legacy/build/pdf";
import { Upload, Settings, Download, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';


pdfjs.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/legacy/build/pdf.worker.mjs';

const PdfViewer = () => {
  const [pdfPages, setPdfPages] = useState([]); // Contient l'image de la page courante
  const [errorMessage, setErrorMessage] = useState("");
  const [currentPage, setCurrentPage] = useState(1); // Page courante
  const [totalPages, setTotalPages] = useState(0);  // Nombre total de pages
  const [pdfBuffer, setPdfBuffer] = useState(null); // Contenu brut du PDF
  const [selectedFile, setSelectedFile] = useState(null); // Nom du fichier sélectionné

  const renderPage = async (pdf, pageNumber) => {
    const page = await pdf.getPage(pageNumber);

    const viewport = page.getViewport({ scale: 1.5 });
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({ canvasContext: context, viewport }).promise;

    return canvas.toDataURL(); // Retourne l'image de la page
  };

  const handlePdfUpload = async (event) => {
    try {
      const file = event.target.files[0];
      if (!file) return;

      setSelectedFile(file.name); // Mettre à jour avec le nom du fichier
      const fileReader = new FileReader();

      fileReader.onload = async (e) => {
        const arrayBuffer = e.target.result;
        setPdfBuffer(arrayBuffer); // Sauvegarder le buffer pour la navigation

        const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;

        setTotalPages(pdf.numPages); // Mettre à jour le nombre total de pages

        const pageImage = await renderPage(pdf, 1);
        setPdfPages([pageImage]); // Mettre à jour l'image de la page courante
      };

      fileReader.readAsArrayBuffer(file); // Lire le fichier
    } catch (error) {
      setErrorMessage(`Erreur lors de la lecture du PDF : ${error.message}`);
      console.error("Détails de l'erreur :", error);
    }
  };

  const changePage = async (newPage) => {
    if (!pdfBuffer) {
      setErrorMessage("Veuillez d'abord charger un fichier PDF.");
      return;
    }

    if (newPage < 1 || newPage > totalPages) return; // Empêcher les dépassements

    const pdf = await pdfjs.getDocument({ data: pdfBuffer }).promise;

    const pageImage = await renderPage(pdf, newPage); // Rendre la page demandée
    setPdfPages([pageImage]); // Mettre à jour l'image de la page
    setCurrentPage(newPage); // Mettre à jour la page courante
  };

  const handleTranslate = () => {
    alert(`Traduction de la page ${currentPage}`);
  };

  return (
    <div className="relative h-[calc(100vh-20px)]">
      {/* Zone d'upload */}
      <div className="mb-2">
        {selectedFile ? (
          <div className="flex items-center space-x-2">
            <p className="text-sm text-gray-600">Fichier sélectionné : {selectedFile}</p>
            <button
              onClick={() => setSelectedFile(null)} // Permet de changer de fichier
              className="text-blue-500 underline text-sm"
            >
              Changer de fichier
            </button>
          </div>
        ) : (
          <input
            type="file"
            accept="application/pdf"
            onChange={handlePdfUpload}
            className="text-sm"
          />
        )}
      </div>

      {errorMessage && <p className="text-red-500">{errorMessage}</p>}

      {/* Conteneur avec défilement */}
      <div className="pdf-container overflow-auto h-[calc(100vh-120px)] border rounded-lg p-4 bg-gray-50">
        {pdfPages.map((page, index) => (
          <img key={index} src={page} alt={`Page ${index + 1}`} className="w-full" />
        ))}
      </div>

      {/* Boutons de navigation */}
      <div
        className="absolute bottom-2 left-1/2 transform -translate-x-1/2 flex items-center space-x-4 bg-white shadow-lg rounded-full px-4 py-2"
      >
        <button
          className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
          onClick={() => changePage(currentPage - 1)}
          disabled={currentPage === 1}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-sm">
          Page {currentPage} of {totalPages}
        </span>
        <button
          className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
          onClick={() => changePage(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          className="ml-2 bg-blue-500 text-white px-4 py-2 rounded-full hover:bg-blue-600 transition-colors"
          onClick={handleTranslate}
        >
          Translate
        </button>
      </div>
    </div>
  );
};

export default PdfViewer;