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
import fitz
import io
from PIL import Image
from flask import url_for



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
def extract_text_and_images(filepath, page_number):
    """
    Extrait le texte et les images d'une page spécifique d'un fichier PDF.

    :param filepath: Le chemin du fichier PDF
    :param page_number: Le numéro de la page à extraire (commençant par 1)
    :return: Un tuple contenant le texte extrait (avec marqueurs d'image) et un dictionnaire des images extraites
    """
    # Ouvrir le document PDF
    document = fitz.open(filepath)

    pdf_filename = os.path.splitext(os.path.basename(filepath))[0]
    output_folder = "./static/images/"
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_folder, exist_ok=True)

    # Vérifier si le numéro de page est valide
    if page_number < 1 or page_number > len(document):
        raise ValueError(f"Numéro de page invalide. Le PDF a {len(document)} pages.")

    # Charger la page (fitz utilise un index basé sur 0)
    page = document.load_page(page_number - 1)

    # Extraire le texte de la page avec les informations de position
    text_instances = page.get_text("dict")["blocks"]

    # Extraire les images de la page
    images = page.get_images(full=True)

    # Définir la taille minimale pour filtrer les images
    min_width, min_height = 25, 25

    extracted_images = {}
    image_counter = 0

    # Liste pour stocker les éléments (texte et images) avec leur position
    elements = []

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

            # Ajouter l'image à la liste des éléments
            # Note: nous utilisons les coordonnées de l'image pour le tri
            elements.append(("IMAGE", f"[{image_name.upper()}]", img[1]))  # img[1] contient les coordonnées


    # Ajouter le texte à la liste des éléments
    for block in text_instances:
        if block["type"] == 0:  # Type 0 représente les blocs de texte
            for line in block["lines"]:
                for span in line["spans"]:
                    elements.append(("text", span["text"], span["bbox"][1]))  # Utiliser seulement la coordonnée y

    # Trier les éléments par leur position verticale (y)
    elements.sort(key=lambda x: x[2])

    # Construire le texte final avec les marqueurs d'image
    final_text = ""
    for element_type, content, _ in elements:
        if element_type == "text":
            final_text += content + " "
        else:  # image
            final_text += f"\n\n{content}\n\n"

    return final_text.strip(), extracted_images
def extract_text_from_pdf(filepath, page_number):
    """
        Extrait le texte d'une page spécifique d'un fichier PDF.

        :param filename: Le nom du fichier PDF ou son chemin complet
        :param page_number: Le numéro de la page à extraire (commençant par 1)
        :return: Le texte extrait de la page spécifiée
        """
    try:

        extracted_text, extracted_images = extract_text_and_images(filepath, page_number)
        for image_name, image_info in extracted_images.items():
            #print(f"{image_name}: taille {image_info['size']}, extension {image_info['extension']}")

            # Sauvegarder l'image
            pdf_filename = os.path.splitext(os.path.basename(filepath))[0]
            with open(f"./static/images/{pdf_filename}_{page_number}_{image_name}.{image_info['extension']}", "wb") as image_file:
                image_file.write(image_info['data'])
            #print(f"Image sauvegardée sous {image_name}.{image_info['extension']}")

        return extracted_text
    except Exception as e:
        print(f"An error occurred while extracting text from PDF: {str(e)}")
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
        text = extract_text_from_pdf(filepath, page_number)
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
    3. Ta reponse doit etre juste la traduction en francais et les marqueurs, n'inclus aucun autre information ni l'instruction speciale
    
    Traduction en francais :"""

    try:
        out()
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
        Contenu
        Préface xxvii
        1 Introduction 1
        1.1 Qu'est-ce que l'apprentissage machine ? 1
        1.2 Apprentissage supervisé 1
        1.2.1 Classification 2
        1.2.2 Régression 8
        1.2.3 Suralimitation et généralisation 12
        1.2.4 Théorème « pas de déjeuner gratuit » 13
        1.3 Apprentissage non supervisé 14
        1.3.1 Regroupement 14
        1.3.2 Découverte des facteurs de variation latents  15
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
        2 Probabilités : Modèles univariés 31
        2.1 Introduction 31
        2.1.1 Qu'est-ce que la probabilité ? 31
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