import gradio as gr
from transformers import (
    LayoutLMv3Processor,
    LayoutLMv3ForSequenceClassification,
    DonutProcessor,
    VisionEncoderDecoderModel
)
import torch
from PIL import Image
import fitz
import os


class ModernPDFExtractor:
    def __init__(self):
        """
        Initialise l'extracteur avec les modèles de Hugging Face pour une analyse
        avancée des documents.
        """
        # Chargement du modèle LayoutLMv3 pour l'analyse de la mise en page
        self.layout_processor = LayoutLMv3Processor.from_pretrained(
            "microsoft/layoutlmv3-base"
        )
        self.layout_model = LayoutLMv3ForSequenceClassification.from_pretrained(
            "microsoft/layoutlmv3-base"
        )

        # Chargement du modèle Donut pour l'extraction du texte
        self.donut_processor = DonutProcessor.from_pretrained(
            "naver-clova-ix/donut-base"
        )
        self.donut_model = VisionEncoderDecoderModel.from_pretrained(
            "naver-clova-ix/donut-base"
        )

        # Déplacement des modèles sur GPU si disponible
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.layout_model.to(self.device)
        self.donut_model.to(self.device)

    def extract_from_pdf(self, pdf_path, output_dir):
        """
        Extrait les images et le texte d'un PDF en utilisant les modèles
        de deep learning pour une meilleure compréhension du contenu.
        """
        os.makedirs(output_dir, exist_ok=True)
        extracted_data = []

        # Ouverture du PDF
        doc = fitz.open(pdf_path)
        base_name = os.path.basename(pdf_path).split('.')[0]

        for page_num in range(doc.page_count):
            # Conversion de la page en image
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Analyse de la mise en page avec LayoutLMv3
            layout_inputs = self.layout_processor(
                images=page_image,
                return_tensors="pt"
            ).to(self.device)

            layout_outputs = self.layout_model(**layout_inputs)
            layout_predictions = layout_outputs.logits.argmax(-1)

            # Extraction du texte avec Donut
            donut_inputs = self.donut_processor(
                images=page_image,
                return_tensors="pt"
            ).to(self.device)

            donut_outputs = self.donut_model.generate(
                **donut_inputs,
                max_length=512,
                num_beams=4
            )

            # Décodage du texte extrait
            extracted_text = self.donut_processor.batch_decode(
                donut_outputs,
                skip_special_tokens=True
            )[0]

            # Analyse des zones d'images dans la mise en page
            for box_idx, prediction in enumerate(layout_predictions[0]):
                if prediction == 1:  # Si la zone est identifiée comme une image
                    try:
                        # Extraction des coordonnées de la zone
                        box = layout_inputs.bbox[0][box_idx].tolist()
                        x0, y0, x1, y1 = [int(coord) for coord in box]

                        # Découpage et sauvegarde de l'image
                        cropped_image = page_image.crop((x0, y0, x1, y1))
                        image_filename = f"{base_name}_page{page_num + 1}_img{box_idx}.png"
                        image_path = os.path.join(output_dir, image_filename)
                        cropped_image.save(image_path, "PNG")

                        # Stockage des données extraites
                        extracted_data.append({
                            'image_path': image_path,
                            'text_context': self.get_text_context(
                                extracted_text,
                                box,
                                layout_inputs.bbox[0]
                            ),
                            'page_num': page_num + 1
                        })

                    except Exception as e:
                        print(f"Erreur lors du traitement de l'image : {str(e)}")

        doc.close()
        return extracted_data

    def get_text_context(self, full_text, image_box, all_boxes, context_size=200):
        """
        Extrait le texte pertinent autour d'une zone d'image en utilisant
        la position relative des boîtes de texte.
        """

        # Calcul de la distance relative entre les boîtes
        def box_distance(box1, box2):
            center1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
            center2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
            return ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5

        # Trouve les boîtes de texte les plus proches de l'image
        nearby_text = []
        for box_idx, box in enumerate(all_boxes):
            distance = box_distance(image_box, box.tolist())
            if distance < context_size:
                nearby_text.append((distance, full_text[box_idx:box_idx + 50]))

        # Trie et combine le texte par proximité
        nearby_text.sort(key=lambda x: x[0])
        return ' '.join(text for _, text in nearby_text[:5])


def process_pdf_with_ml(file, query):
    """
    Fonction principale pour l'interface Gradio qui utilise les modèles
    de machine learning pour l'extraction.
    """
    extractor = ModernPDFExtractor()
    output_dir = "uploads/markdown/images"

    # Extraction des images et du texte
    results = extractor.extract_from_pdf(file.name, output_dir)

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
    return "Aucune image trouvée", None


# Interface Gradio simplifiée
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
    title="Extracteur PDF intelligent avec LayoutLM et Donut",
    description="Extraction d'images et de texte basée sur l'intelligence artificielle"
)

if __name__ == "__main__":
    iface.launch()