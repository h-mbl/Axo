import fitz  # PyMuPDF
import io
from PIL import Image
import os
from whoosh.fields import *
from whoosh.index import create_in
from whoosh.qparser import QueryParser
import shutil


def extract_and_index_pdf_images(pdf_path, output_dir):
    """
    Extrait les images d'un PDF et crée un index searchable basé sur le texte environnant.

    Args:
        pdf_path: Chemin vers le fichier PDF
        output_dir: Dossier de sortie pour les images
    """
    # Création des dossiers nécessaires
    os.makedirs(output_dir, exist_ok=True)
    index_dir = "indexes"
    os.makedirs(index_dir, exist_ok=True)

    # Création du schéma d'index
    schema = Schema(
        file_name=ID(stored=True),
        content=TEXT(stored=True),
        page_num=NUMERIC(stored=True),
        image_path=ID(stored=True)
    )

    # Création de l'index
    ix = create_in(index_dir, schema)
    writer = ix.writer()

    # Ouverture du document PDF
    doc = fitz.open(pdf_path)
    base_name = os.path.basename(pdf_path).split('.')[0]

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)

        # Extraction du texte de la page pour le contexte
        text_dict = page.get_text("dict")

        # Configuration pour une meilleure qualité d'image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Traitement des blocs de la page
        for block_num, block in enumerate(text_dict.get("blocks", [])):
            if "image" in block:
                try:
                    # Extraction des coordonnées de l'image
                    bbox = block["bbox"]
                    x0, y0, x1, y1 = [int(coord * 2) for coord in bbox]  # *2 car Matrix(2, 2)

                    # Vérification de la taille minimale
                    if (x1 - x0) < 100 or (y1 - y0) < 100:  # Ignore les très petites images
                        continue

                    # Extraction de l'image
                    cropped_image = page_image.crop((x0, y0, x1, y1))

                    # Génération du nom de fichier
                    image_filename = f"{base_name}_page{page_num + 1}_img{block_num}.png"
                    image_path = os.path.join(output_dir, image_filename)

                    # Sauvegarde de l'image
                    cropped_image.save(image_path, "PNG")

                    # Extraction du texte environnant
                    surrounding_text = get_surrounding_text(text_dict["blocks"], block_num)

                    # Ajout à l'index
                    writer.add_document(
                        file_name=image_filename,
                        content=surrounding_text,
                        page_num=page_num + 1,
                        image_path=image_path
                    )

                    print(f"Image extraite : {image_filename}")
                    print(f"Texte associé : {surrounding_text[:100]}...")

                except Exception as e:
                    print(f"Erreur lors du traitement de l'image : {str(e)}")

    writer.commit()
    doc.close()
    return ix


def get_surrounding_text(blocks, current_block_index, context_size=3):
    """
    Extrait le texte environnant un bloc d'image.
    """
    text = []
    start_idx = max(0, current_block_index - context_size)
    end_idx = min(len(blocks), current_block_index + context_size + 1)

    for block in blocks[start_idx:end_idx]:
        if "text" in block:
            text.append(block["text"])
        elif "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text.append(span.get("text", ""))

    return " ".join(text)


def search_images(index, query, limit=5):
    """
    Recherche des images basée sur le texte environnant.
    """
    with index.searcher() as searcher:
        query_parser = QueryParser("content", index.schema)
        query = query_parser.parse(query)
        results = searcher.search(query, limit=limit)

        found_images = []
        for hit in results:
            found_images.append({
                'image_path': hit['image_path'],
                'page_num': hit['page_num'],
                'text': hit['content'][:200],  # Premiers 200 caractères du contexte
                'score': hit.score
            })

        return found_images

# Exemple d'utilisation
pdf_path = "uploads/plannification_strategie.pdf"
output_dir = "uploads/markdown/images"

# Extraction et indexation
index = extract_and_index_pdf_images(pdf_path, output_dir)

# Recherche d'images (optionnel)
results = search_images(index, "votre terme de recherche")
for result in results:
    print(f"Image trouvée : {result['image_path']}")
    print(f"Page : {result['page_num']}")
    print(f"Contexte : {result['text']}")
    print(f"Score : {result['score']}")
    print("---")