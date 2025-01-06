import re
from flask import Flask, render_template, request, jsonify , g
import os
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import base64
from io import BytesIO
import PyPDF2
import json
from groq import Groq
import fitz
import io
from PIL import Image
from flask import url_for



app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
IMAGES_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}
#data = json.load(open('privates.json'))
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
groq_client = Groq(api_key=GROQ_API_KEY)


#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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


def extract_text_and_images(filepath, page_number):
    """
    Extrait le texte et les images d'une page spécifique d'un fichier PDF.

    :param filepath: Le chemin du fichier PDF
    :param page_number: Le numéro de la page à extraire (commençant par 1)
    :return: Un tuple contenant le texte extrait (avec marqueurs d'image) et un dictionnaire des images extraites
    """
    # Ouvrir le document PDF
    document = fitz.open(filepath)

    # Créer le dossier de sortie pour les images si nécessaire
    output_folder = "./static/images/"
    os.makedirs(output_folder, exist_ok=True)

    # Vérifier si le numéro de page est valide
    if page_number < 1 or page_number > len(document):
        raise ValueError(f"Numéro de page invalide. Le PDF a {len(document)} pages.")

    # Charger la page (fitz utilise un index basé sur 0)
    page = document.load_page(page_number - 1)

    # Extraire le texte et les images
    text_instances = page.get_text("dict")["blocks"]
    images = page.get_images(full=True)

    # Définir la taille minimale pour filtrer les images
    min_width, min_height = 25, 25
    extracted_images = {}
    image_counter = 0

    # Liste pour stocker les éléments (texte et images) avec leur position
    elements = []

    # Parcourir et traiter les images
    for img in images:
        xref = img[0]
        base_image = document.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]

        # Charger l'image avec PIL pour obtenir ses dimensions
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size

        # Filtrer les images selon leur taille
        if width >= min_width and height >= min_height:
            image_counter += 1
            image_name = f"image{image_counter}"
            extracted_images[image_name] = {
                "data": image_bytes,
                "extension": image_ext,
                "size": (width, height)
            }
            coords = img[1] if isinstance(img[1], tuple) else (0, 0)
            elements.append(("IMAGE", f"[{image_name.upper()}]", coords))

    # Ajouter le texte à la liste des éléments
    for block in text_instances:
        if block["type"] == 0:  # Type 0 représente les blocs de texte
            for line in block["lines"]:
                for span in line["spans"]:
                    elements.append(
                        ("TEXT", span["text"], span["bbox"]))  # Utiliser la boîte englobante complète (bbox)

        # Fonction pour obtenir la coordonnée y pour le tri

    def get_y_coordinate(element):
        _, _, coords = element
        if isinstance(coords, (tuple, list)) and len(coords) > 1:
            return coords[1]
        return 0  # Valeur par défaut si les coordonnées ne sont pas valides

    # Trier les éléments par leur position verticale (y)

    elements.sort(key=get_y_coordinate) # Trier en fonction de la coordonnée y (position en haut)

    # Construire le texte final avec les marqueurs d'image tout en gardant la mise en page
    final_text = ""
    current_y = 0  # Variable pour suivre la position actuelle en y

    for element_type, content, coords in elements:
        if element_type == "TEXT":
            if isinstance(coords, (tuple, list)) and len(coords) > 1:
                if abs(coords[1] - current_y) > 5:
                    final_text += "\n"
                final_text += content
                current_y = coords[3] if len(coords) > 3 else coords[1]
            else:
                final_text += content
        elif element_type == "IMAGE":
            final_text += f"\n\n{content}\n\n"
            current_y = -1

    return final_text.strip(), extracted_images


def extract_text_from_pdf(filepath, page_number):
    """
    Extrait le texte d'une page spécifique d'un fichier PDF, incluant les images avec des marqueurs.

    :param filepath: Le chemin du fichier PDF
    :param page_number: Le numéro de la page à extraire (commençant par 1)
    :return: Le texte extrait de la page spécifiée, avec des marqueurs d'images
    """
    try:
        extracted_text, extracted_images = extract_text_and_images(filepath, page_number)

        # Sauvegarder les images extraites
        for image_name, image_info in extracted_images.items():
            pdf_filename = os.path.splitext(os.path.basename(filepath))[0]
            #image_path = f"./static/images/{pdf_filename}_{page_number}_{image_name}.{image_info['extension']}"
            image_path = os.path.join(app.config['IMAGES_FOLDER'],
                                      f"{pdf_filename}_{page_number}_{image_name}.{image_info['extension']}")

            # Enregistrer l'image dans le dossier de sortie
            with open(image_path, "wb") as image_file:
                image_file.write(image_info['data'])
            print(f"Image sauvegardée sous {image_path}")

        return extracted_text
    except Exception as e:
        print(f"Une erreur est survenue lors de l'extraction du texte : {str(e)}")
        return None
def preprocess_translation(translation,filename,page_number):
    # Remplacer tous les types d'espaces par des espaces normaux
    translation = re.sub(r'[\xa0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f]+', ' ', translation)

    lines = translation.split('\n')
    processed_lines = []
    prev_indent = 0
    image_pattern = r'\[IMAGE\d+\]'

    # Extraire le nom de base du fichier (sans extension)
    base_filename = os.path.splitext(filename)[0]

    for line in lines:
        # Préserver les marqueurs d'image
        if re.match(image_pattern, line.strip()):
            line = line.lower().strip().replace('[', '').replace(']','')
            image_url = url_for('static', filename=f'images/{base_filename}_{str(page_number)}_{line}.png')
            img_tag = f'<img src="{image_url}" alt="{line}" class="translated-image">'
            processed_lines.append(f'<div class="image-container">{img_tag}</div>')

            continue

        # Ignorer les lignes vides
        if not line.strip():
            continue

        # Détecter l'indentation
        indent_match = re.match(r'^(\s*)', line)
        indent = len(indent_match.group(1)) if indent_match else 0

        # Nettoyer la ligne
        clean_line = line.strip()

        # Détecter le format de la ligne (numéro + texte ou juste texte)
        number_match = re.match(r'^((?:\d+\.)*\d+)\s+(.+)$', clean_line)

        if number_match:
            number, text = number_match.groups()
            # Calculer l'indentation relative
            relative_indent = max(0, indent - prev_indent)
            processed_line = (
                f'<div class="toc-item" style="padding-left: {relative_indent * 20}px;">'
                f'<span class="toc-number">{number}</span> '
                f'<span class="toc-text">{text}</span>'
                f'</div>'
            )
        else:
            # Pour les lignes sans numéro (comme "Contents" ou "Preface")
            processed_line = f'<div class="toc-item toc-header">{clean_line}</div>'

        processed_lines.append(processed_line)
        prev_indent = indent

    return "\n".join(processed_lines)

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
        a = 0
        text = extract_text_from_pdf(filepath, page_number)
        a = 0
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'extraction du texte du PDF: {str(e)}'}), 500

    if not text:
        return jsonify({'error': 'Le texte à traduire est vide'}), 400

    if hasattr(g, 'book_info'):
        book_info = g.book_info
    else:
        book_info = extract_book_info("", filename)

    prompt = f"""Tu es un traducteur professionnel. Traduis le passage suivant du livre '{book_info.get('title', 'Titre inconnu')}' de l'auteur {book_info.get('author', 'Auteur inconnu')} de l'anglais vers le francais. Voici le texte à traduire :
    
    {text}
    
    Instructions spéciales :
    1. Conserve les marqueurs [IMAGEx] tels quels dans ta traduction, où x est un numéro, ne change pas ce tag par pitie si tu vois par exemple [IMAGE100] garde ce mot comme ca  
    2. Traduis le contenu textuel mais laisse les noms propres et les termes techniques inchangés.
    3. Ta reponse doit etre juste la traduction en francais et les marqueurs, n'inclus aucune autre information dans ta reponse
    
    Traduction en francais :"""

    try:
        #out()
        # model="llama-3.1-70b-versatile",
        completion = groq_client.chat.completions.create(
            model="llama3-groq-70b-8192-tool-use-preview",
            messages=[
                {"role": "system", "content": "Tu es un traducteur professionnel spécialisé dans la traduction littéraire de l'anglais vers le francais."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        translation = completion.choices[0].message.content.strip()
        print(translation)
        formatted_translation = preprocess_translation(translation,filename,page_number)
        return jsonify({'translated_text':  formatted_translation})
    except :
        translation = f"""
        Contents
Preface
xxvii
1
Introduction
11.1
What is machine learning?
11.2
Supervised learning
11.2.1
Classiﬁcation
21.2.2
Regression
81.2.3
Overﬁtting and generalization
121.2.4
No free lunch theorem
131.3
Unsupervised learning
141.3.1
Clustering
141.3.2
Discovering latent “factors of variation”
151.3.3
Self-supervised learning
161.3.4
Evaluating unsupervised learning
161.4
Reinforcement learning
171.5
Data
191.5.1
Some common image datasets
191.5.2
Some common text datasets
211.5.3
Preprocessing discrete input data
231.5.4
Preprocessing text data
241.5.5
Handling missing data
261.6
Discussion
271.6.1
The relationship between ML and other ﬁelds
271.6.2
Structure of the book
281.6.3
Caveats
28
I
Foundations
29
2
Probability: Univariate Models
312.1
Introduction
312.1.1
What is probability?
31
                """
        formatted_translation = preprocess_translation(translation,filename,page_number)

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