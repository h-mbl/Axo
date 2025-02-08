# PDF Translator

An advanced PDF translation platform that preserves document layout and formatting while providing accurate translations across multiple languages.

![PDF Translator Preview](https://raw.githubusercontent.com/username/pdf-translator/main/preview.png)

## 🚀 Features

### PDF Translation
- Translate PDF content while preserving layout and formatting
- Support for multiple languages via Groq and HuggingFace translation engines
- Maintain original document structure and visual elements
- Smart caching system for improved performance
- Export to HTML with layout preservation

### 📸 Preview

Here's how our PDF Translator works:


#### Final Result
![Translated Document](https://raw.githubusercontent.com/username/pdf-translator/main/docs/translated-doc.png)
*Get your translated document with preserved formatting*

## 🛠️ Tech Stack

### Backend
- Python FastAPI
- PDF extraction and processing
- Multiple translation services integration
- Caching system
- Layout preservation algorithms

### Frontend
- React
- Tailwind CSS
- Vite
- PDF viewer integration

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Node.js 16+
- npm or yarn



### Environment Variables
Create `.env` files in both backend and frontend directories:

Backend `.env`:
```
GROQ_API_KEY=your_groq_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key
```
