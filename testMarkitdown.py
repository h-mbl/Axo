import fitz  # PyMuPDF
import os
from pathlib import Path
import logging
from markitdown import MarkItDown
import hashlib


class PDFConverter:
    def __init__(self):
        self.md = MarkItDown()
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def extract_images(self, pdf_path, images_dir):
        """
        Extrait les images d'un PDF en utilisant PyMuPDF.
        Retourne une liste des chemins des images extraites.
        """
        image_paths = []
        doc = fitz.open(pdf_path)

        # Pour chaque page du PDF
        for page_num in range(doc.page_count):
            page = doc[page_num]

            # Obtenir les images de la page
            image_list = page.get_images()

            self.logger.info(f"Found {len(image_list)} images on page {page_num + 1}")

            # Pour chaque image dans la page
            for img_index, img in enumerate(image_list):
                try:
                    # Obtenir l'image
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    # Générer un nom unique pour l'image
                    image_ext = base_image["ext"]
                    image_hash = hashlib.md5(image_bytes).hexdigest()[:8]
                    image_filename = f"image_p{page_num + 1}_{img_index + 1}_{image_hash}.{image_ext}"
                    image_path = images_dir / image_filename

                    # Sauvegarder l'image
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)

                    image_paths.append(image_path)
                    self.logger.info(f"Saved image: {image_path}")

                except Exception as e:
                    self.logger.error(f"Error extracting image: {str(e)}")
                    continue

        doc.close()
        return image_paths

    def convert_with_images(self, pdf_path):
        base_path = Path(pdf_path)
        output_dir = base_path.parent / 'markdown'
        images_dir = output_dir / 'images'
        markdown_file = output_dir / f"{base_path.stem}.md"

        self.logger.info(f"Starting conversion of {pdf_path}")

        # Créer les répertoires nécessaires
        output_dir.mkdir(exist_ok=True)
        images_dir.mkdir(exist_ok=True)

        try:
            # Extraire les images avec PyMuPDF
            image_paths = self.extract_images(pdf_path, images_dir)

            # Convertir le texte avec MarkItDown
            result = self.md.convert(str(pdf_path))
            content = result.text_content

            # Insérer les références des images dans le markdown
            for idx, image_path in enumerate(image_paths):
                relative_path = os.path.relpath(image_path, output_dir)
                # Ajouter la référence de l'image dans le markdown
                image_reference = f"\n![Image {idx + 1}]({relative_path.replace(os.sep, '/')})\n"
                content += image_reference

            # Sauvegarder le contenu markdown
            with open(markdown_file, 'w', encoding='utf-8') as md_file:
                md_file.write(content)

            result_info = {
                'markdown_path': str(markdown_file),
                'images_dir': str(images_dir),
                'processed_images': [str(p) for p in image_paths],
                'success': True,
                'message': f"Conversion successful. File saved to {markdown_file}",
                'stats': {
                    'total_images': len(image_paths),
                    'processed_images': len(image_paths)
                }
            }

            self.logger.info("Conversion completed successfully")
            self.logger.debug(f"Conversion stats: {result_info['stats']}")

            return result_info

        except Exception as error:
            self.logger.error(f"Conversion failed: {str(error)}", exc_info=True)
            return {
                'success': False,
                'message': f"Error during conversion: {str(error)}"
            }


def main():
    converter = PDFConverter()
    pdf_path = "uploads/plannification_strategie.pdf"

    result = converter.convert_with_images(pdf_path)

    if result['success']:
        print("\nConversion completed successfully:")
        print(f"- Markdown file: {result['markdown_path']}")
        print(f"- Images directory: {result['images_dir']}")
        print(f"- Processed images: {len(result['processed_images'])}")
        print(f"- Total images found: {result['stats']['total_images']}")

        if result['processed_images']:
            print("\nExtracted images:")
            for img_path in result['processed_images']:
                print(f"  - {img_path}")
    else:
        print(f"\nConversion failed:")
        print(f"- Error: {result['message']}")


if __name__ == "__main__":
    main()