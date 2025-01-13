// Configuration de base pour les appels API
const API_BASE_URL = 'http://localhost:8000';

export const translationService = {
  // Fonction pour envoyer une demande de traduction
  async translatePdfPage(pdfFile, pageNumber, sourceLanguage, targetLanguage) {
    try {
      // Création d'un FormData pour envoyer le fichier
      const formData = new FormData();
      formData.append('file', pdfFile);
      formData.append('page_number', pageNumber);
      formData.append('source_language', sourceLanguage);
      formData.append('target_language', targetLanguage);

      const response = await fetch(`${API_BASE_URL}/translate`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Erreur lors de la traduction:', error);
      throw error;
    }
  }
};