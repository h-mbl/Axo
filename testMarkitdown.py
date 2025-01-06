from markitdown import MarkItDown
import os

# Création d'une instance de base de MarkItDown pour la conversion de documents
md = MarkItDown()

# Définition des chemins d'entrée et de sortie
chemin_entree = "uploads/plannification_strategie.pdf"
# Création du nom du fichier de sortie en gardant le même nom mais avec extension .md
nom_fichier = os.path.splitext(os.path.basename(chemin_entree))[0]
chemin_sortie = f"uploads/markdown/{nom_fichier}.md"

try:
    # Création du dossier de sortie s'il n'existe pas
    os.makedirs(os.path.dirname(chemin_sortie), exist_ok=True)

    # Conversion du fichier PDF en format Markdown
    resultat = md.convert(chemin_entree)

    # Sauvegarde du contenu converti dans le fichier Markdown
    with open(chemin_sortie, 'w', encoding='utf-8') as fichier_markdown:
        fichier_markdown.write(resultat.text_content)

    print(f"Conversion réussie ! Le fichier a été sauvegardé dans : {chemin_sortie}")

except Exception as erreur:
    print(f"Une erreur est survenue lors de la conversion : {str(erreur)}")