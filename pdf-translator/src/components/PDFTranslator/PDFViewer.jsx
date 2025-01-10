// PDFViewer.jsx
import React, { useState } from "react";
import * as pdfjs from "pdfjs-dist/legacy/build/pdf";
import { Upload, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw, RotateCw } from 'lucide-react';

pdfjs.GlobalWorkerOptions.workerSrc = '/node_modules/pdfjs-dist/legacy/build/pdf.worker.mjs';

const PdfViewer = () => {
  const [pdfPages, setPdfPages] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [pdfBuffer, setPdfBuffer] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1.5);
  const [rotationAngle, setRotationAngle] = useState(0);

  const renderPage = async (pdf, pageNumber) => {
    const page = await pdf.getPage(pageNumber);
    const viewport = page.getViewport({ scale: zoomLevel, rotation: rotationAngle });

    const canvas = document.createElement("canvas");
    const context = canvas.getContext("2d");
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({ canvasContext: context, viewport }).promise;
    return canvas.toDataURL();
  };

  const handlePdfUpload = async (event) => {
    try {
      const file = event.target.files[0];
      if (!file) return;

      const fileReader = new FileReader();
      fileReader.onload = async (e) => {
        const arrayBuffer = e.target.result;
        setPdfBuffer(arrayBuffer);

        const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
        setTotalPages(pdf.numPages);

        const pageImage = await renderPage(pdf, 1);
        setPdfPages([pageImage]);
      };

      fileReader.readAsArrayBuffer(file);
    } catch (error) {
      setErrorMessage(`Error loading PDF: ${error.message}`);
      console.error(error);
    }
  };

  const changePage = async (newPage) => {
    if (newPage < 1 || newPage > totalPages || !pdfBuffer) return;
    const pdf = await pdfjs.getDocument({ data: pdfBuffer }).promise;
    const pageImage = await renderPage(pdf, newPage);
    setPdfPages([pageImage]);
    setCurrentPage(newPage);
  };

  const adjustZoom = (zoomIn) => {
    setZoomLevel((prev) => Math.max(0.5, Math.min(3, zoomIn ? prev + 0.2 : prev - 0.2)));
  };

  const rotate = (clockwise) => {
    setRotationAngle((prev) => (prev + (clockwise ? 90 : -90)) % 360);
  };

  return (
    <div className="relative h-full flex flex-col">
      <div className="mb-2 flex items-center justify-between">
        <input
          type="file"
          accept="application/pdf"
          onChange={handlePdfUpload}
          className="text-sm"
        />
        <div className="flex space-x-2">
          <button
            onClick={() => adjustZoom(true)}
            className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full">
            <ZoomIn className="w-5 h-5" />
          </button>
          <button
            onClick={() => adjustZoom(false)}
            className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full">
            <ZoomOut className="w-5 h-5" />
          </button>
          <button
            onClick={() => rotate(false)}
            className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full">
            <RotateCcw className="w-5 h-5" />
          </button>
          <button
            onClick={() => rotate(true)}
            className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full">
            <RotateCw className="w-5 h-5" />
          </button>
        </div>
      </div>
      {errorMessage && <p className="text-red-500">{errorMessage}</p>}
      <div className="pdf-container overflow-auto h-[calc(100vh-180px)] border rounded-lg p-4 bg-gray-50">
        {pdfPages.map((page, index) => (
          <img key={index} src={page} alt={`Page ${index + 1}`} className="w-full" />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-center space-x-4">
        <button
          onClick={() => changePage(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full disabled:opacity-50">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="text-sm">Page {currentPage} of {totalPages}</span>
        <button
          onClick={() => changePage(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full disabled:opacity-50">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default PdfViewer;
