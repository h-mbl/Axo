from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import base64
from io import BytesIO
import PyPDF2
import requests
import json
from PyPDF2 import PdfReader
from groq import Groq

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
data = json.load(open('privates.json'))
GROQ_API_KEY = data['GROQ_API_KEY']
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Initialisez le client Groq
groq_client = Groq(api_key=GROQ_API_KEY)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier n\'a été envoyé'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier n\'a été sélectionné'}), 400

    #La fonction allowed_file() vérifie probablement l'extension du fichier pour s'assurer qu'il s'agit d'un type de fichier accepté
    # (par exemple, uniquement des PDF

    if file and allowed_file(file.filename):
        # nettoyer le nom du fichier. Elle supprime tous les caractères potentiellement dangereux ou problématiques du nom de fichier,
        # rendant le nom sûr à utiliser dans un système de fichiers.

        filename = secure_filename(file.filename)
        #Cette ligne construit le chemin complet où le fichier sera sauvegardé.
        # Elle combine le dossier d'upload (défini dans la configuration de l'application)

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        #Cette ligne sauvegarde effectivement le fichier uploadé à l'emplacement spécifié par filepath.
        file.save(filepath)

        #cette ligne renvoie une réponse JSON au client
        return jsonify({'success': True, 'filename': filename}), 200
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/', methods=['GET', 'POST'])
def index():
    # au lancement si la methode n'est pas post alors il affiche index.html
    if request.method == 'POST':
        a = 0
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


def extract_book_info_from_filename(filename):
    # Implémentez cette fonction pour extraire les informations du livre à partir du nom de fichier
    # Par exemple, si le format est "Titre - Auteur.pdf", vous pouvez le parser ici
    parts = filename.rsplit('.', 1)[0].split(' - ')
    return {
        'title': parts[0] if len(parts) > 0 else 'Titre inconnu',
        'author': parts[1] if len(parts) > 1 else 'Auteur inconnu'
    }


def extract_text_from_pdf(filename, page_number):
    """
        Extrait le texte d'une page spécifique d'un fichier PDF.

        :param filename: Le nom du fichier PDF ou son chemin complet
        :param page_number: Le numéro de la page à extraire (commençant par 1)
        :return: Le texte extrait de la page spécifiée
        """
    try:
        # Vérifier si le fichier existe
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Le fichier {filename} n'existe pas.")

        # Ouvrir le fichier PDF
        with open(filename, 'rb') as file:
            reader = PdfReader(file)

            # Vérifier si le numéro de page est valide
            if page_number < 1 or page_number > len(reader.pages):
                raise ValueError(
                    f"Le numéro de page {page_number} est invalide. Le PDF contient {len(reader.pages)} pages.")

            # Extraire le texte de la page spécifiée
            page = reader.pages[page_number - 1]  # PyPDF2 utilise un index basé sur 0
            text = page.extract_text()

            # Vérifier si le texte a été extrait avec succès
            if not text.strip():
                print(
                    f"Avertissement : La page {page_number} semble être vide ou ne contient pas de texte extractible.")

            return text

    except Exception as e:
        print(f"Une erreur s'est produite lors de l'extraction du texte : {str(e)}")
        raise


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

    book_info = extract_book_info_from_filename(filename)

    prompt = f"Tu es un traducteur professionnel. Traduis le passage suivant du livre '{book_info.get('title', 'Titre inconnu')}' de l'auteur {book_info.get('author', 'Auteur inconnu')} de l'anglais vers le francais. Voici le texte à traduire :\n\n{text}\n\nTraduction en anglais :"

    try:
        completion = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "Tu es un traducteur professionnel spécialisé dans la traduction littéraire du français vers l'anglais."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        translation = completion.choices[0].message.content.strip()
        app.logger.info(f"Traduction réussie. Premiers caractères : {translation[:50]}...")
        return jsonify({'translated_text': translation})
    except Exception as e:
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


if __name__ == '__main__':
    a = 0
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=False)