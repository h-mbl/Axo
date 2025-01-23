# backend/app/services/content_organizer.py

class ContentOrganizer:
    @staticmethod
    def convert_extracted_image_to_dict(img):
        return {
            'type': 'image',
            'path': str(img.path),
            'bbox': list(map(float, img.bbox)),
            'width': float(img.size[0]) if img.size else None,
            'height': float(img.size[1]) if img.size else None,
            'caption': str(img.caption),
            'context_text': str(img.context_text),
            'page_number': int(img.page_number),
            'marker': str(img.marker)
        }

    @staticmethod
    def organize_blocks_into_sections(text_blocks, translated_parts, images):
        """
        Organise les blocs de texte et les images en sections logiques.
        Maintenant adapté pour travailler avec des dictionnaires au lieu d'objets TextBlock.
        """
        sections = []
        current_section = []
        last_y_position = 0
        space_threshold = 50

        # Conversion et tri des images par position verticale
        image_blocks = [text_blocks.convert_extracted_image_to_dict(img) for img in images]
        image_blocks.sort(key=lambda x: x['bbox'][1])

        # Traitement des blocs de texte
        for i, (block, translated_text) in enumerate(zip(text_blocks, translated_parts)):
            # Maintenant block est un dictionnaire, donc nous accédons à ses propriétés avec la notation de dictionnaire
            current_y = block['bbox'][1]  # Changé de block.bbox[1]

            # Insérer les images avant ce bloc de texte si nécessaire
            while image_blocks and image_blocks[0]['bbox'][1] <= current_y:
                img_block = image_blocks.pop(0)
                if current_section:
                    sections.append(current_section)
                current_section = []
                current_section.append(img_block)

            # Création du bloc traduit
            translated_block = {
                'type': 'text',
                'content': translated_text,
                'bbox': block['bbox'],  # Changé de block.bbox
                'style': {
                    'fontSize': f"{block['font_size']}px",  # Changé de block.font_size
                    'fontFamily': block['font_name'],  # Changé de block.font_name
                    'fontWeight': block['font_weight'],  # Changé de block.font_weight
                    'textAlign': block['text_alignment'],  # Changé de block.text_alignment
                    'lineHeight': f"{block['line_height']}px",  # Changé de block.line_height
                    'transform': f"rotate({block['rotation']}deg)",  # Changé de block.rotation
                    'color': block['color']  # Changé de block.color
                }
            }

            # Vérification pour nouvelle section
            vertical_gap = block['bbox'][1] - last_y_position if current_section else 0
            if (not current_section or
                    vertical_gap > space_threshold or
                    block.get('is_title', False)):  # Changé de getattr(block, 'is_title', False)
                if current_section:
                    sections.append(current_section)
                current_section = []

            current_section.append(translated_block)
            last_y_position = block['bbox'][3]  # Changé de block.bbox[3]

        # Ajouter les images restantes
        for img_block in image_blocks:
            if current_section:
                sections.append(current_section)
            current_section = [img_block]

        # Ajouter la dernière section
        if current_section:
            sections.append(current_section)

        return sections
