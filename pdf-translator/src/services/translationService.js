import apiClient from './apiService';

export const translationService = {
  async translatePdfPage(pdfFile, pageNumber, sourceLanguage, targetLanguage) {
    try {
      if (!pdfFile) {
        throw new Error('Fichier PDF requis');
      }

      const formData = new FormData();
      formData.append('file', pdfFile);
      formData.append('page_number', pageNumber.toString());
      formData.append('source_language', sourceLanguage);
      formData.append('target_language', targetLanguage);

      console.log('Préparation de la requête de traduction:', {
        pageNumber,
        sourceLanguage,
        targetLanguage,
        fileName: pdfFile.name,
        fileSize: pdfFile.size
      });

      const response = await apiClient.post('/translate', formData, {
        headers: {
          // Ne pas définir Content-Type - il sera automatiquement défini avec le boundary
          'Accept': 'application/json',
        },
        // Augmenter le timeout pour les gros fichiers
        timeout: 60000,
      });

      return response.data;

    } catch (error) {
      console.error('Erreur de traduction:', error);

      if (error.response) {
        throw new Error(error.response.data.detail || 'Erreur du serveur de traduction');
      } else if (error.request) {
        throw new Error('Impossible de contacter le serveur de traduction');
      } else {
        throw new Error(`Erreur: ${error.message}`);
      }
    }
  }
};