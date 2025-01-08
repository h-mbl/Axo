import gradio as gr
from transformers import (
    LayoutLMv3Processor,
    LayoutLMv3ForDocumentQuestionAnswering
)
import torch
from PIL import Image
import fitz
import os


class ModernPDFExtractor:
    def __init__(self):
        """
        Initialise l'extracteur avec un modèle pré-entraîné pour l'analyse de documents
        """
        # Utilisation d'un modèle pré-entraîné pour la QA sur documents
        self.processor = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-finetuned-docvqa"
        )
        self.model = LayoutLMv3ForDocumentQuestionAnswering.from_pretrained(
            "microsoft/layoutlmv3-finetuned-docvqa"
        )

        # Déplacement du modèle sur GPU si disponible
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Utilisation de : {self.device}")
        self.model.to(self.device)

    def extract_from_pdf(self, pdf_path, output_dir):
        """
        Extrait les images et le texte d'un PDF
        """
        os.makedirs(output_dir, exist_ok=True)
        extracted_data = []

        # Ouverture du PDF
        print(f"Traitement du PDF : {pdf_path}")
        doc = fitz.open(pdf_path)
        base_name = os.path.basename(pdf_path).split('.')[0]

        for page_num in range(doc.page_count):
            print(f"Traitement de la page {page_num + 1}/{doc.page_count}")

            # Conversion de la page en image
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            try:
                # Recherche d'images dans la page
                image_list = page.get_images()

                for img_idx, img in enumerate(image_list):
                    try:
                        # Extraction de l'image
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Conversion en image PIL
                        image = Image.open(io.BytesIO(image_bytes))

                        # Sauvegarde de l'image
                        image_filename = f"{base_name}_page{page_num + 1}_img{img_idx}.png"
                        image_path = os.path.join(output_dir, image_filename)
                        image.save(image_path)

                        # Analyse du texte environnant
                        encoding = self.processor(
                            image,
                            "Quel est le contexte de cette image?",
                            return_tensors="pt",
                            truncation=True
                        )

                        # Déplacer les tenseurs sur le device approprié
                        for key in encoding.keys():
                            if isinstance(encoding[key], torch.Tensor):
                                encoding[key] = encoding[key].to(self.device)

                        # Obtention de la réponse du modèle
                        outputs = self.model(**encoding)
                        predicted_answer = self.processor.tokenizer.decode(
                            outputs.logits.argmax(-1).squeeze().tolist(),
                            skip_special_tokens=True
                        )

                        extracted_data.append({
                            'image_path': image_path,
                            'text_context': predicted_answer,
                            'page_num': page_num + 1
                        })

                        print(f"Image extraite : {image_filename}")

                    except Exception as e:
                        print(f"Erreur lors du traitement de l'image {img_idx} : {str(e)}")

            except Exception as e:
                print(f"Erreur lors du traitement de la page {page_num + 1} : {str(e)}")

        doc.close()
        return extracted_data


def process_pdf_with_ml(file, query):
    """
    Fonction principale pour l'interface Gradio
    """
    try:
        extractor = ModernPDFExtractor()
        output_dir = "uploads/markdown/images"

        print("Début de l'extraction...")
        results = extractor.extract_from_pdf(file.name, output_dir)

        if not results:
            return "Aucune image trouvée", None

        print(f"Nombre d'images extraites : {len(results)}")

        # Recherche simple basée sur la correspondance de texte
        best_match = None
        best_score = 0

        for result in results:
            # Calcul simple de similarité avec la requête
            score = sum(word in result['text_context'].lower()
                        for word in query.lower().split())
            if score > best_score:
                best_score = score
                best_match = result

        if best_match:
            return best_match['text_context'], Image.open(best_match['image_path'])

        return "Aucune correspondance trouvée", None

    except Exception as e:
        print(f"Erreur lors du traitement : {str(e)}")
        return f"Une erreur est survenue : {str(e)}", None


# Interface Gradio
iface = gr.Interface(
    fn=process_pdf_with_ml,
    inputs=[
        gr.File(label="Fichier PDF"),
        gr.Textbox(label="Rechercher une image")
    ],
    outputs=[
        gr.Textbox(label="Texte trouvé"),
        gr.Image(type="pil", label="Image trouvée")
    ],
    title="Extracteur PDF intelligent avec LayoutLMv3",
    description="Upload d'un PDF pour extraire et rechercher des images avec leur contexte"
)

if __name__ == "__main__":
    print("Démarrage de l'interface...")
    iface.launch()