from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import base64
from io import BytesIO
import PyPDF2
import requests
import json

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
data = json.load(open('privates.json'))
GROQ_API_KEY = data['GROQ_API_KEY']
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', error='No file part')
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error='No selected file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Get total number of pages and extract book info
            with open(filepath, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                # Extract book info from the first page (you might need to adjust this)
                first_page = pdf_reader.pages[0].extract_text()
                book_info = extract_book_info(first_page)
            return render_template('index.html', filename=filename, current_page=1, total_pages=total_pages, book_info=book_info)
    return render_template('index.html')

def extract_book_info(text):
    # Cette fonction est un exemple simplifié. Vous devrez l'adapter en fonction de la structure de vos PDF.
    lines = text.split('\n')
    title = lines[0] if lines else "Unknown Title"
    author = lines[1] if len(lines) > 1 else "Unknown Author"
    return {"title": title, "author": author}

@app.route('/translate', methods=['POST'])
def translate():
    print("je suis ici")
    text = request.form['text']
    book_info = request.form['book_info']
    breakpoint()
    if 'text' not in request.form or 'book_info' not in request.form:
        print("error 1")
        return jsonify({'error': 'Données manquantes dans la requête'}), 400

    text = request.form['text']
    book_info = request.form['book_info']
    print(book_info)

    try:
        book_info = json.loads(book_info)

    except json.JSONDecodeError:
        print("error 1")
        return jsonify({'error': 'Format invalide pour book_info'}), 400

    if not text:
        print("error 1")
        return jsonify({'error': 'Le texte à traduire est vide'}), 400

    prompt = f"Tu es un traducteur professionnel. Traduis le passage suivant du livre '{book_info.get('title', 'Titre inconnu')}' de l'auteur {book_info.get('author', 'Auteur inconnu')} du français vers l'anglais. Voici le texte à traduire :\n\n{text}\n\nTraduction en anglais :"
    print(prompt)
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "Tu es un traducteur professionnel spécialisé dans la traduction littéraire du français vers l'anglais."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()  # Cela lèvera une exception pour les codes d'état HTTP d'erreur
        translation = response.json()['choices'][0]['message']['content'].strip()
        return jsonify({'translated_text': translation})
    except requests.RequestException as e:
        app.logger.error(f"Erreur lors de l'appel à l'API Groq: {str(e)}")
        return jsonify({'error': 'La traduction a échoué'}), 500

@app.route('/get_page', methods=['POST'])
def get_page():
    filename = request.form['filename']
    page_number = int(request.form['page_number'])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Convert the specific page to an image
    images = convert_from_path(filepath, first_page=page_number, last_page=page_number)
    img = images[0]

    # Convert the image to base64 for embedding in HTML
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Extract text from the page
    with open(filepath, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        page = pdf_reader.pages[page_number - 1]
        text = page.extract_text()

    return jsonify({'image': img_str, 'text': text})

"""
@app.route('/translate', methods=['POST'])
def translate():
    text = request.form['text']
    target_lang = request.form['target_lang']

    prompt = f"Translate the following text to {target_lang}:\n\n{text}\n\nTranslation:"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-70b-versatile",  # or another model you prefer
        "messages": [
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000  # adjust as needed
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=data)

    if response.status_code == 200:
        translation = response.json()['choices'][0]['message']['content'].strip()
        return jsonify({'translated_text': translation})
    else:
        return jsonify({'error': 'Translation failed'}), 500
"""

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)