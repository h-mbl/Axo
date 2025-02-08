# PDF Translator

An advanced PDF translation platform that preserves document layout and formatting while providing accurate translations across multiple languages.
![PDF Translator Preview](https://github.com/user-attachments/assets/9325bb90-06a2-4a34-886a-b0610f62c480)


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
![image](https://github.com/user-attachments/assets/51f4591a-cbec-4378-80ae-bc8c9e0e151f)


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
