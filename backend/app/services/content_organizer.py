# backend/app/services/content_organizer.py
from backend.app.models.data_models import ElementType, LayoutElement, ElementPriority


class ContentOrganizer:
    def __init__(self):
        self.page_width: float = 0
        self.page_height: float = 0

    def calculate_element_priority(self, element: dict) -> ElementPriority:
        """Calculate priority based on element properties"""
        if element['type'] == 'image':
            area = (element['bbox'][2] - element['bbox'][0]) * (element['bbox'][3] - element['bbox'][1])
            if area > (self.page_width * self.page_height * 0.15):  # Large images
                return ElementPriority.CRITICAL
            return ElementPriority.HIGH

        if element.get('is_title', False):
            return ElementPriority.CRITICAL

        if element.get('font_size', 0) > 14:  # Larger text
            return ElementPriority.HIGH

        return ElementPriority.MEDIUM

    def create_layout_element(self, block: dict) -> LayoutElement:
        """Convert a block to a LayoutElement with priority information"""
        element_type = ElementType.IMAGE if block.get('type') == 'image' else ElementType.TEXT
        if element_type == ElementType.TEXT and block.get('is_title', False):
            element_type = ElementType.HEADING

        bbox = block['bbox']
        size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        original_position = (bbox[0], bbox[1])

        priority = self.calculate_element_priority(block)

        return LayoutElement(
            content=block.get('content', '') if element_type != ElementType.IMAGE else block.get('path', ''),
            element_type=element_type,
            bbox=bbox,
            priority=priority,
            size=size,
            original_position=original_position,
            font_size=block.get('font_size'),
            font_name=block.get('font_name'),
            font_weight=block.get('font_weight'),
            text_alignment=block.get('text_alignment'),
            line_height=block.get('line_height'),
            rotation=block.get('rotation'),
            color=block.get('color'),
            page_number=block.get('page_number')
        )

    def organize_blocks_into_sections(self, text_blocks: list[dict],
                                      translated_parts: list[str],
                                      images: list) -> list[list[dict]]:
        """Enhanced version with priority-based organization"""
        # Set page dimensions from first block if available
        if text_blocks:
            self.page_width = max(block['bbox'][2] for block in text_blocks)
            self.page_height = max(block['bbox'][3] for block in text_blocks)

        # Convert all elements to LayoutElements
        layout_elements = []

        # Process images first as anchors
        for img in images:
            layout_elements.append(self.create_layout_element(
                ContentOrganizer.convert_extracted_image_to_dict(img)))

        # Process text blocks
        for block, translated_text in zip(text_blocks, translated_parts):
            block['content'] = translated_text
            layout_elements.append(self.create_layout_element(block))

        # Sort by priority
        layout_elements.sort(key=lambda x: x.priority.value, reverse=True)

        # Group into sections while maintaining priority
        sections = []
        current_section = []
        last_y_position = 0
        space_threshold = 50

        for element in layout_elements:
            if element.element_type == ElementType.IMAGE:
                # Images start new sections
                if current_section:
                    sections.append(current_section)
                current_section = [self._convert_layout_element_to_dict(element)]
            else:
                vertical_gap = element.bbox[1] - last_y_position if current_section else 0

                if vertical_gap > space_threshold:
                    if current_section:
                        sections.append(current_section)
                    current_section = []

                current_section.append(self._convert_layout_element_to_dict(element))
                last_y_position = element.bbox[3]

        if current_section:
            sections.append(current_section)

        return sections

    @staticmethod
    def _convert_layout_element_to_dict(element: LayoutElement) -> dict:
        """Convert LayoutElement back to dictionary format for HTML export"""
        if element.element_type == ElementType.IMAGE:
            return {
                'type': 'image',
                'path': element.content,
                'bbox': element.bbox
            }
        else:
            return {
                'type': 'text',
                'content': element.content,
                'bbox': element.bbox,
                'style': {
                    'fontSize': f"{element.font_size}px" if element.font_size else None,
                    'fontFamily': element.font_name,
                    'fontWeight': element.font_weight,
                    'textAlign': element.text_alignment,
                    'lineHeight': f"{element.line_height}px" if element.line_height else None,
                    'transform': f"rotate({element.rotation}deg)" if element.rotation else None,
                    'color': element.color
                }
            }

    @staticmethod
    def convert_extracted_image_to_dict(img) -> dict:
        """
        Convertit un objet ExtractedImage en dictionnaire pour le traitement.
        Cette méthode est essentielle pour la standardisation du format des images
        avant leur intégration dans le système de priorité.

        Args:
            img: Objet ExtractedImage contenant les informations de l'image

        Returns:
            dict: Dictionnaire contenant les informations formatées de l'image
        """
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