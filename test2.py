import fitz
import io
from PIL import Image


def extract_text_and_images(filepath, page_number):
    """
    Extrait le texte et les images d'une page spécifique d'un fichier PDF.

    :param filepath: Le chemin du fichier PDF
    :param page_number: Le numéro de la page à extraire (commençant par 1)
    :return: Un tuple contenant le texte extrait (avec marqueurs d'image) et un dictionnaire des images extraites
    """
    # Ouvrir le document PDF
    document = fitz.open(filepath)

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
            elements.append(("image", f"[{image_name}]", img[1]))  # img[1] contient les coordonnées

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


# Exemple d'utilisation
filepath = "uploads/pdf-test.pdf"
page_number = 1

try:
    extracted_text, extracted_images = extract_text_and_images(filepath, page_number)

    print("Texte extrait (avec marqueurs d'image):")
    print(extracted_text)

    print("\nImages extraites:")
    for image_name, image_info in extracted_images.items():
        print(f"{image_name}: taille {image_info['size']}, extension {image_info['extension']}")

        # Sauvegarder l'image
        with open(f"{image_name}.{image_info['extension']}", "wb") as image_file:
            image_file.write(image_info['data'])
        print(f"Image sauvegardée sous {image_name}.{image_info['extension']}")

except Exception as e:
    print(f"Une erreur s'est produite : {str(e)}")