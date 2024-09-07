import fitz
import io
from PIL import Image


def extract_text_and_images(filepath, page_number):
    """
    Extrait le texte et les images d'une page spécifique d'un fichier PDF avec une meilleure gestion de la mise en page.

    :param filepath: Le chemin du fichier PDF
    :param page_number: Le numéro de la page à extraire (commençant par 1)
    :return: Un tuple contenant le texte extrait (avec marqueurs d'image) et un dictionnaire des images extraites
    """
    document = fitz.open(filepath)

    if page_number < 1 or page_number > len(document):
        raise ValueError(f"Numéro de page invalide. Le PDF a {len(document)} pages.")

    page = document.load_page(page_number - 1)

    text_instances = page.get_text("dict")["blocks"]
    images = page.get_images(full=True)

    min_width, min_height = 25, 25

    extracted_images = {}
    image_counter = 0
    elements = []

    # Traitement des images
    for img in images:
        xref = img[0]
        base_image = document.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]

        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size

        if width >= min_width and height >= min_height:
            image_counter += 1
            image_name = f"image{image_counter}"
            extracted_images[image_name] = {
                "data": image_bytes,
                "extension": image_ext,
                "size": (width, height)
            }

            # Utiliser les coordonnées de l'image pour le positionnement
            bbox = page.get_image_bbox(img)
            if bbox:
                x0, y0, x1, y1 = bbox
                elements.append(("image", f"[{image_name}]", (x0, y0, x1, y1)))

    # Traitement du texte
    for block in text_instances:
        if block["type"] == 0:  # Type 0 représente les blocs de texte
            for line in block["lines"]:
                for span in line["spans"]:
                    elements.append(("text", span["text"], span["bbox"]))

    # Trier les éléments par leur position (d'abord y, puis x)
    elements.sort(key=lambda x: (x[2][1], x[2][0]))

    final_text = ""
    last_y1 = 0
    last_x1 = 0
    line_height_threshold = 5  # Ajustez cette valeur selon vos besoins

    for i, (element_type, content, bbox) in enumerate(elements):
        x0, y0, x1, y1 = bbox

        # Décider s'il faut ajouter un saut de ligne
        if y0 - last_y1 > line_height_threshold:
            final_text += "\n"
        elif element_type == "image" and i > 0 and elements[i - 1][0] == "text":
            # Si c'est une image qui suit du texte, toujours ajouter un saut de ligne
            final_text += "\n"

        if element_type == "text":
            # Ajouter un espace si nécessaire
            if x0 - last_x1 > 1:  # Ajustez cette valeur selon vos besoins
                final_text += " "
            final_text += content
        else:  # image
            final_text += f"\n{content}\n"

        last_y1 = y1
        last_x1 = x1

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