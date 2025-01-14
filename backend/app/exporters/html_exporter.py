class HTMLExporter:
    def export(self, translated_blocks: list, images: list, output_path: str):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                .page-content { position: relative; }
                .text-block { position: absolute; }
                .image-block { position: absolute; }
            </style>
        </head>
        <body>
        <div class="page-content">
        """

        # Ajouter les blocs de texte et images
        for block in translated_blocks:
            if block['type'] == 'text':
                html_content += f"""
                <div class="text-block" style="
                    left: {block['bbox'][0]}px;
                    top: {block['bbox'][1]}px;
                    width: {block['bbox'][2] - block['bbox'][0]}px;
                    ">
                    {block['content']}
                </div>
                """
            elif block['type'] == 'image':
                html_content += f"""
                <img class="image-block" 
                    src="{block['path']}"
                    style="
                        left: {block['bbox'][0]}px;
                        top: {block['bbox'][1]}px;
                        width: {block['bbox'][2] - block['bbox'][0]}px;
                    "
                >
                """

        html_content += """
        </div>
        </body>
        </html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)