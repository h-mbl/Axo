import gradio as gr
import fitz
from PIL import Image
import io
import os
from whoosh.fields import *
from whoosh.index import create_in
from whoosh.qparser import QueryParser


class PDFImageExtractor:
    def __init__(self):
        """
        Initialise l'extracteur avec des attributs pour stocker l'index
        et le répertoire temporaire des images.
        """
        self.index = None
        self.temp_dir = None

    def extract_and_index(self, pdf_path, output_dir, dpi=300):
        """
        Extrait les images d'un PDF et crée un index de recherche basé sur
        le texte qui entoure chaque image.
        """
        # Création du dossier de sortie si nécessaire
        os.makedirs(output_dir, exist_ok=True)

        # Définition du schéma d'indexation pour la recherche
        schema = Schema(
            file_name=ID(stored=True),  # Nom du fichier image
            content=TEXT(stored=True),  # Texte autour de l'image
            image_path=ID(stored=True)  # Chemin complet de l'image
        )

        # Création du dossier et de l'index pour la recherche
        index_dir = "indexes"
        os.makedirs(index_dir, exist_ok=True)
        self.index = create_in(index_dir, schema)
        writer = self.index.writer()

        # Ouverture et traitement du PDF
        doc = fitz.open(pdf_path)
        base_name = os.path.basename(pdf_path).split('.')[0]

        # Parcours de chaque page du PDF
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)

            # Extraction du texte et création d'une image haute qualité de la page
            text_dict = page.get_text("dict")
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Double la résolution
            page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Traitement de chaque bloc de la page
            for block_num, block in enumerate(text_dict.get("blocks", [])):
                if "image" in block:  # Si le bloc contient une image
                    try:
                        # Extraction des coordonnées de l'image
                        bbox = block["bbox"]
                        x0, y0, x1, y1 = [int(coord * 2) for coord in bbox]

                        # Découpage de l'image
                        cropped_image = page_image.crop((x0, y0, x1, y1))

                        # Génération du nom de fichier et sauvegarde
                        image_filename = f"{base_name}_page{page_num + 1}_img{block_num}.png"
                        image_path = os.path.join(output_dir, image_filename)
                        cropped_image.save(image_path, "PNG")

                        # Extraction du texte environnant
                        surrounding_text = self.get_surrounding_text(
                            text_dict["blocks"],
                            block_num
                        )

                        # Indexation de l'image et de son contexte
                        writer.add_document(
                            file_name=image_filename,
                            content=surrounding_text,
                            image_path=image_path
                        )

                    except Exception as e:
                        print(f"Erreur lors du traitement de l'image : {str(e)}")

        writer.commit()
        doc.close()
        self.temp_dir = output_dir
        return self.index

    def get_surrounding_text(self, blocks, current_block_index, context_size=3):
        """
        Extrait le texte qui se trouve avant et après une image dans le PDF.
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

    def search(self, query, limit=1):
        """
        Recherche les images correspondant à une requête textuelle.
        """
        if not self.index:
            return None, None

        with self.index.searcher() as searcher:
            query_parser = QueryParser("content", self.index.schema)
            parsed_query = query_parser.parse(query)
            results = searcher.search(parsed_query, limit=limit)

            if not results:
                return "Aucune image trouvée", None

            hit = results[0]
            # Retourne le contexte et l'image trouvée
            return hit['content'][:200], Image.open(hit['image_path'])


def process_pdf(file, dpi, skip_front, skip_back, skip_block, query):
    """
    Fonction principale qui traite le PDF et retourne les résultats.
    Cette fonction est appelée par l'interface Gradio.
    """
    extractor = PDFImageExtractor()
    output_dir = "uploads/markdown/images"

    # Extraction et indexation des images
    extractor.extract_and_index(
        file.name,
        output_dir,
        dpi=dpi
    )

    # Recherche d'images
    title, image = extractor.search(query)
    return title, image


# Configuration de l'interface utilisateur avec Gradio
iface = gr.Interface(
    fn=process_pdf,
    inputs=[
        gr.File(label="Fichier PDF"),
        gr.Slider(minimum=72, maximum=600, value=300, label="Qualité de l'image (DPI)"),
        gr.Number(value=0, label="Pages à ignorer au début"),
        gr.Number(value=1, label="Pages à ignorer à la fin"),
        gr.Number(value=5, label="Blocs à ignorer"),
        gr.Textbox(label="Rechercher une image")
    ],
    outputs=[
        gr.Textbox(label="Texte trouvé"),
        gr.Image(type="pil", label="Image trouvée")
    ],
    title="Extracteur d'images PDF avec recherche",
    description="Téléchargez un PDF pour en extraire les images et les rechercher par leur contexte textuel"
)

if __name__ == "__main__":
    iface.launch()