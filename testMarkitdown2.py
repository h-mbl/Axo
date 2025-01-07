import pdfplumber
import os
from pathlib import Path
import logging
from markitdown import MarkItDown
import hashlib
from PIL import Image
import io


class PDFConverter:
    def __init__(self):
        self.md = MarkItDown()
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def extract_images(self, pdf_path, images_dir):
        """
        Extrait les images d'un PDF en utilisant pdfplumber.
        Retourne une liste des chemins des images extraites.
        """
        image_paths = []

        # Ouvrir le PDF avec pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            self.logger.info(f"Processing PDF with {len(pdf.pages)} pages")

            # Pour chaque page du PDF
            for page_num, page in enumerate(pdf.pages):
                # Obtenir les images de la page
                images = page.images

                self.logger.info(f"Found {len(images)} images on page {page_num + 1}")

                # Pour chaque image dans la page
                for img_index, img in enumerate(images):
                    try:
                        # Extraire les données de l'image
                        image_bytes = img['stream'].get_data()

                        # Générer un nom unique pour l'image
                        image_hash = hashlib.md5(image_bytes).hexdigest()[:8]

                        # Déterminer l'extension de l'image basée sur le type de stream
                        stream_type = img.get('stream', {}).get('/Subtype', '')
                        if '/JPXDecode' in img.get('stream', {}).get('/Filter', []):
                            ext = 'jp2'
                        elif stream_type == '/Image':
                            ext = 'png'  # Par défaut, on utilise PNG
                        else:
                            ext = 'png'

                        # Créer le nom du fichier
                        image_filename = f"image_p{page_num + 1}_{img_index + 1}_{image_hash}.{ext}"
                        image_path = images_dir / image_filename

                        # Obtenir les métadonnées de l'image
                        width = img.get('width', 0)
                        height = img.get('height', 0)
                        x0 = img.get('x0', 0)
                        y0 = img.get('y0', 0)

                        self.logger.debug(f"Image details: {width}x{height} at position ({x0}, {y0})")

                        # Sauvegarder l'image
                        try:
                            # Essayer de convertir les données en image avec PIL
                            image = Image.open(io.BytesIO(image_bytes))
                            image.save(str(image_path))

                            image_paths.append({
                                'path': image_path,
                                'width': width,
                                'height': height,
                                'x': x0,
                                'y': y0,
                                'page': page_num + 1
                            })

                            self.logger.info(f"Saved image: {image_path}")

                        except Exception as e:
                            self.logger.error(f"Error saving image: {str(e)}")
                            continue

                    except Exception as e:
                        self.logger.error(f"Error processing image on page {page_num + 1}: {str(e)}")
                        continue

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
            # Extraire les images avec pdfplumber
            image_paths = self.extract_images(pdf_path, images_dir)

            # Convertir le texte avec MarkItDown
            result = self.md.convert(str(pdf_path))
            content = result.text_content

            # Trier les images par page et position
            sorted_images = sorted(image_paths, key=lambda x: (x['page'], x['y'], x['x']))

            # Insérer les références des images dans le markdown
            for idx, img_info in enumerate(sorted_images):
                image_path = img_info['path']
                relative_path = os.path.relpath(image_path, output_dir)
                # Créer une légende incluant les dimensions de l'image
                caption = f"Image {idx + 1} (Page {img_info['page']}, {img_info['width']}x{img_info['height']})"
                image_reference = f"\n![{caption}]({relative_path.replace(os.sep, '/')})\n"
                content += image_reference

            # Sauvegarder le contenu markdown
            with open(markdown_file, 'w', encoding='utf-8') as md_file:
                md_file.write(content)

            result_info = {
                'markdown_path': str(markdown_file),
                'images_dir': str(images_dir),
                'processed_images': [str(img['path']) for img in image_paths],
                'success': True,
                'message': f"Conversion successful. File saved to {markdown_file}",
                'stats': {
                    'total_images': len(image_paths),
                    'processed_images': len(image_paths),
                    'images_by_page': {
                        page: len([img for img in image_paths if img['page'] == page])
                        for page in set(img['page'] for img in image_paths)
                    }
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

        if result['stats']['images_by_page']:
            print("\nImages par page:")
            for page, count in result['stats']['images_by_page'].items():
                print(f"  Page {page}: {count} image(s)")

        if result['processed_images']:
            print("\nExtracted images:")
            for img_path in result['processed_images']:
                print(f"  - {img_path}")
    else:
        print(f"\nConversion failed:")
        print(f"- Error: {result['message']}")


if __name__ == "__main__":
    main()