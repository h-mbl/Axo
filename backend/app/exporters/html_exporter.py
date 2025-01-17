import os


class HTMLExporter:
    def export(self, translated_blocks: list, images: list, output_path: str):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                .page-content {
                    position: relative;
                    width: 100%;
                    min-height: 1000px;  /* Ajuster selon vos besoins */
                    margin: 0 auto;
                    background-color: white;
                }
                .text-block {
                    position: absolute;
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    margin: 0;
                    padding: 0;
                }
                .image-block {
                    position: absolute;
                    max-width: 100%;
                    height: auto;
                    object-fit: contain;
                }
            </style>
        </head>
        <body>
        <div class="page-content">
        """

        # Trier les blocs par position verticale
        sorted_blocks = sorted(translated_blocks, key=lambda x: x['bbox'][1])

        for block in sorted_blocks:
            if block['type'] == 'text' and block['content'].strip():
                # Calcul des dimensions relatives
                left = f"{block['bbox'][0]}px"
                top = f"{block['bbox'][1]}px"
                width = f"{block['bbox'][2] - block['bbox'][0]}px"

                html_content += f"""
                <div class="text-block" style="
                    left: {left};
                    top: {top};
                    width: {width};
                    ">
                    {block['content']}
                </div>
                """
            elif block['type'] == 'image':
                # Gestion des images avec dimensions relatives
                left = f"{block['bbox'][0]}px"
                top = f"{block['bbox'][1]}px"
                width = f"{block['bbox'][2] - block['bbox'][0]}px"

                # Utiliser un chemin relatif pour l'image
                image_path = block['path']
                if not image_path.startswith(('http://', 'https://', '/')):
                    image_path = f"../images/{os.path.basename(image_path)}"

                html_content += f"""
                <img class="image-block" 
                    src="{image_path}"
                    alt="Image extraite du PDF"
                    style="
                        left: {left};
                        top: {top};
                        width: {width};
                    "
                >
                """

        html_content += """
        </div>
        </body>
        </html>
        """

        # Créer le répertoire de sortie s'il n'existe pas
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)