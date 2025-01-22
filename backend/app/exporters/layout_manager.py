# layout_manager.py

from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np


@dataclass
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


class LayoutManager:
    def __init__(self, page_width: float, page_height: float):
        self.page_width = page_width
        self.page_height = page_height
        self.occupied_spaces = []

    def adjust_positions(self, blocks: List[Dict]) -> List[Dict]:
        """Adjusts positions of blocks to prevent overlapping."""
        adjusted_blocks = []

        # Sort blocks by y-position to maintain reading order
        blocks.sort(key=lambda x: x['bbox'][1])

        for block in blocks:
            if block['type'] == 'text':
                # Calculate new size based on content
                new_bbox = self._calculate_text_bbox(block)
                # Find new position if overlap exists
                adjusted_pos = self._find_available_space(new_bbox)
                block['bbox'] = adjusted_pos
            elif block['type'] == 'image':
                # Images are fixed elements, mark their space as occupied
                self.occupied_spaces.append(block['bbox'])

            adjusted_blocks.append(block)

        return adjusted_blocks

    def _calculate_text_bbox(self, block: Dict) -> List[float]:
        """Calculates new bounding box based on text content and style."""
        # Extract style information
        font_size = float(block['style']['fontSize'].replace('px', ''))
        line_height = float(block['style']['lineHeight'].replace('px', ''))

        # Estimate text width and height
        text_length = len(block['content'])
        estimated_width = text_length * (font_size * 0.6)  # Approximate character width
        estimated_height = line_height

        return [
            block['bbox'][0],  # Keep original x
            block['bbox'][1],  # Keep original y
            estimated_width,
            estimated_height
        ]

    def _find_available_space(self, bbox: List[float]) -> List[float]:
        """Finds non-overlapping position for the block."""
        current_pos = bbox.copy()

        while self._check_overlap(current_pos):
            # Try moving down if overlap exists
            current_pos[1] += 5  # Small increment

            # If reaching page bottom, move to next column
            if current_pos[1] + current_pos[3] > self.page_height:
                current_pos[1] = 0  # Reset y position
                current_pos[0] += current_pos[2] + 20  # Move to next column

        self.occupied_spaces.append(current_pos)
        return current_pos

    def _check_overlap(self, bbox: List[float]) -> bool:
        """Checks if the given bbox overlaps with any occupied space."""
        for occupied in self.occupied_spaces:
            if (bbox[0] < occupied[0] + occupied[2] and
                    bbox[0] + bbox[2] > occupied[0] and
                    bbox[1] < occupied[1] + occupied[3] and
                    bbox[1] + bbox[3] > occupied[1]):
                return True
        return False