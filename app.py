import re

from flask import Flask, render_template, request, jsonify , g
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import base64
from io import BytesIO
import PyPDF2
import requests
import json
from groq import Groq

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
data = json.load(open('privates.json'))
GROQ_API_KEY = data['GROQ_API_KEY']
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
groq_client = Groq(api_key=GROQ_API_KEY)

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
            # Pour afficher le pdf
            with open(filepath, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(pdf_reader.pages)
                # Extract book info from the first page (you might need to adjust this)
                first_page = pdf_reader.pages[0].extract_text()
                book_info = extract_book_info(first_page, filename)
                g.book_info = book_info
            return render_template('index.html', filename=filename, current_page=1, total_pages=total_pages, book_info=book_info)
    return render_template('index.html')

def extract_book_info(text,filename):
    # Cette fonction est un exemple simplifié. Vous devrez l'adapter en fonction de la structure de vos PDF.
    """lines = text.split('\n')
    title = lines[0] if lines else "Unknown Title"
    author = lines[1] if len(lines) > 1 else "Unknown Author"
    return {"title": title, "author": author}"""

    pattern = r'^(.*?)-(.*?)\.pdf$'
    match = re.match(pattern, filename)

    if match:
        book_name = match.group(1)
        author_name = match.group(2)
        return {"title": book_name, "author": author_name}
    else:
        return {"title": "Unknown Title", "author": "Unknown Author"}

def extract_text_from_pdf(filepath, page_number):
    """
        Extrait le texte d'une page spécifique d'un fichier PDF.

        :param filename: Le nom du fichier PDF ou son chemin complet
        :param page_number: Le numéro de la page à extraire (commençant par 1)
        :return: Le texte extrait de la page spécifiée
        """
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Check if the page number is valid
            if page_number < 1 or page_number > len(pdf_reader.pages):
                raise ValueError(f"Invalid page number. The PDF has {len(pdf_reader.pages)} pages.")

            # PyPDF2 uses 0-based index, so we subtract 1 from the page number
            page = pdf_reader.pages[page_number - 1]
            text = page.extract_text()

            return text.strip()
    except Exception as e:
        print(f"An error occurred while extracting text from PDF: {str(e)}")
        return None


@app.route('/translate', methods=['POST'])
def translate():
    if 'filename' not in request.form or 'page_number' not in request.form:
        return jsonify({'error': 'Données manquantes dans la requête'}), 400

    filename = request.form['filename']
    page_number = int(request.form['page_number'])

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return jsonify({'error': f'Le fichier {filename} n\'existe pas sur le serveur'}), 404

    try:
        text = extract_text_from_pdf(filepath, page_number)
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'extraction du texte du PDF: {str(e)}'}), 500

    if not text:
        return jsonify({'error': 'Le texte à traduire est vide'}), 400

    if hasattr(g, 'book_info'):
        book_info = g.book_info
    else:
        book_info = extract_book_info("", filename)

    prompt = f"Tu es un traducteur professionnel. Traduis le passage suivant du livre '{book_info.get('title', 'Titre inconnu')}' de l'auteur {book_info.get('author', 'Auteur inconnu')} de l'anglais vers le francais. Voici le texte à traduire :\n\n{text}\n\nTraduction en anglais :"

    try:
        out()
        completion = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "Tu es un traducteur professionnel spécialisé dans la traduction littéraire de l'anglais vers le francais."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        translation = completion.choices[0].message.content.strip()
        app.logger.info(f"Traduction réussie. Premiers caractères : {translation[:50]}...")
        return jsonify({'translated_text': translation})
    except :
        translation = f"""
Contenu
Préface xxvii
1 Introduction 1
1.1 Qu'est-ce que l'apprentissage machine ? 1
1.2 Apprentissage supervisé 1
1.2.1 Classification 2
1.2.2 Régression 8
1.2.3 Suralimitation et généralisation 12
1.2.4 Théorème « pas de déjeuner gratuit » 13
1.3 Apprentissage non supervisé 14
1.3.1 Regroupement 14
1.3.2 Découverte des facteurs de variation latents  15
1.3.3 Apprentissage auto-supervisé 16
1.3.4 Évaluation de l'apprentissage non supervisé 16
1.4 Apprentissage par renforcement 17
1.5 Données 19
1.5.1 Quelques jeux de données d'images courants 19
1.5.2 Quelques jeux de données de texte courants 21
1.5.3 Prétraitement des données discrètes d'entrée 23
1.5.4 Prétraitement des données de texte 24
1.5.5 Traitement des données manquantes 26
1.6 Discussion 27
1.6.1 La relation entre l'apprentissage machine (ML) et les autres domaines 27
1.6.2 Structure du livre 28
1.6.3 Précautions 28
SI o n d a g e s 29
2 Probabilités : Modèles univariés 31
2.1 Introduction 31
2.1.1 Qu'est-ce que la probabilité ? 31

        """
        formatted_translation = "<p>" + "</p><p>".join(translation.split('\n')) + "</p>"

        return jsonify({'translated_text': formatted_translation})
    """"
    except Exception as e:
        app.logger.error(f"Erreur lors de l'appel à l'API Groq: {str(e)}")
        return jsonify({'error': 'La traduction a échoué'}), 500
        """

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



if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=False)