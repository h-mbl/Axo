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

  // Fonction pour rendre une page
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

  // Fonction pour charger le PDF
  const handlePdfUpload = async (event) => {
    try {
      setErrorMessage("");
      const file = event.target.files[0];
      if (!file) return;

      const fileReader = new FileReader();

      fileReader.onload = async (e) => {
         const arrayBuffer = e.target.result; // Résultat brut du FileReader

          if (arrayBuffer instanceof ArrayBuffer) {
            setPdfBuffer(arrayBuffer); // Sauvegarder le buffer
            const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;

            setTotalPages(pdf.numPages); // Mettre à jour le nombre total de pages

            // Rendre et afficher uniquement la première page
            const pageImage = await renderPage(pdf, 1);
            setPdfPages([pageImage]); // Mettre à jour l'image de la page courante
          } else {
            console.error("Le fichier n'est pas un ArrayBuffer valide.");
          }
      };

      fileReader.readAsArrayBuffer(file); // Lire le fichier
    } catch (error) {
      setErrorMessage(`Erreur lors de la lecture du PDF : ${error.message}`);
      console.error("Détails de l'erreur :", error);
    }
  };

  // Fonction pour changer de page
  const changePage = async (newPage) => {
    if (newPage < 1 || newPage > totalPages) return; // Empêcher les dépassements

    const pdf = await pdfjs.getDocument({ data: pdfBuffer }).promise;

    const pageImage = await renderPage(pdf, newPage); // Rendre la page demandée
    setPdfPages([pageImage]); // Mettre à jour l'image de la page
    setCurrentPage(newPage); // Mettre à jour la page courante
  };

  // Fonction pour traduire une page (simple exemple)
  const handleTranslate = () => {
    alert(`Traduction de la page ${currentPage}`);
  };

  return (
    <div>
      {/* Zone d'upload */}
      <input
        type="file"
        accept="application/pdf"
        onChange={handlePdfUpload}
        className="mb-4"
      />
      {errorMessage && <p className="text-red-500">{errorMessage}</p>}

      {/* Affichage de la page courante */}
      <div className="mt-4">
        {pdfPages.map((page, index) => (
          <img key={index} src={page} alt={`Page ${index + 1}`} />
        ))}
      </div>

      {/* Boutons de navigation */}
      <div
        className="fixed bottom-6 left-1/2 transform -translate-x-1/2 flex items-center space-x-4 bg-white shadow-lg rounded-full px-4 py-2"
      >
        {/* Bouton Précédent */}
        <button
          className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
          onClick={() => changePage(currentPage - 1)}
          disabled={currentPage === 1}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Texte indiquant la page courante */}
        <span className="text-sm">
          Page {currentPage} of {totalPages}
        </span>

        {/* Bouton Suivant */}
        <button
          className="p-2 hover:bg-gray-100 rounded-full disabled:opacity-50"
          onClick={() => changePage(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Bouton Translate */}
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