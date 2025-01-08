import fitz  # PyMuPDF
import io
from PIL import Image


def extract_images_from_pdf(pdf_path, output_dir):
    # Ouvre le document PDF
    pdf_document = fitz.open(pdf_path)

    # Pour chaque page du PDF
    for page_number in range(pdf_document.page_count):
        # Récupère la page
        page = pdf_document[page_number]

        # Liste toutes les images de la page
        image_list = page.get_images()

        # Pour chaque image trouvée
        for image_index, img in enumerate(image_list):
            # Récupère les données de l'image
            xref = img[0]  # référence de l'image
            base_image = pdf_document.extract_image(xref)

            if base_image:
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]  # extension de l'image (png, jpeg, etc.)

                # Convertit les bytes en image
                image = Image.open(io.BytesIO(image_bytes))

                # Sauvegarde l'image
                image_filename = f"{output_dir}/page_{page_number + 1}_image_{image_index + 1}.{image_ext}"
                image.save(image_filename)

    pdf_document.close()

extract_images_from_pdf("uploads/plannification_strategie.pdf", "uploads/markdown/images")