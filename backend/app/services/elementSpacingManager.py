from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np


@dataclass
class ElementBounds:
    x1: float
    y1: float
    x2: float
    y2: float
    element_type: str
    margin: float = 20.0  # Marge de sécurité autour de l'élément


class ElementSpacingManager:
    def __init__(self, page_width: float, page_height: float):
        self.page_width = page_width
        self.page_height = page_height
        self.elements: List[ElementBounds] = []
        self.min_vertical_spacing = 30.0  # Espacement minimal entre les éléments

    def add_element(self, bounds: ElementBounds) -> ElementBounds:
        """
        Ajoute un élément en ajustant sa position pour éviter les chevauchements.
        """
        # Si c'est une image, on la traite en priorité
        if bounds.element_type == 'image':
            return self._position_image(bounds)
        return self._position_text(bounds)

    def _position_image(self, bounds: ElementBounds) -> ElementBounds:
        """
        Positionne une image en évitant les chevauchements et en respectant les marges.
        """
        # Largeur et hauteur de l'image
        width = bounds.x2 - bounds.x1
        height = bounds.y2 - bounds.y1

        # Chercher le meilleur emplacement
        best_position = None
        min_overlap = float('inf')

        # Positions possibles : en haut de la page ou après le dernier élément
        possible_y_positions = [0]  # Commencer en haut de la page
        if self.elements:
            possible_y_positions.append(max(el.y2 for el in self.elements) + self.min_vertical_spacing)

        for y_pos in possible_y_positions:
            # Essayer différentes positions horizontales
            for x_pos in [0, (self.page_width - width) / 2, self.page_width - width]:
                new_bounds = ElementBounds(
                    x1=x_pos,
                    y1=y_pos,
                    x2=x_pos + width,
                    y2=y_pos + height,
                    element_type='image',
                    margin=bounds.margin
                )

                overlap = self._calculate_overlap(new_bounds)
                if overlap < min_overlap:
                    min_overlap = overlap
                    best_position = new_bounds

        if best_position:
            self.elements.append(best_position)
            return best_position

        # Si aucune position optimale n'est trouvée, placer après le dernier élément
        last_y = max((el.y2 for el in self.elements), default=0) + self.min_vertical_spacing
        final_bounds = ElementBounds(
            x1=bounds.x1,
            y1=last_y,
            x2=bounds.x2,
            y2=last_y + height,
            element_type='image',
            margin=bounds.margin
        )
        self.elements.append(final_bounds)
        return final_bounds

    def _position_text(self, bounds: ElementBounds) -> ElementBounds:
        """
        Positionne un bloc de texte en évitant les chevauchements.
        """
        # Hauteur du texte
        height = bounds.y2 - bounds.y1

        # Trouver la position verticale appropriée
        last_y = max((el.y2 for el in self.elements), default=0)
        new_y = last_y + self.min_vertical_spacing

        # Créer les nouvelles limites
        new_bounds = ElementBounds(
            x1=bounds.x1,
            y1=new_y,
            x2=bounds.x2,
            y2=new_y + height,
            element_type='text',
            margin=bounds.margin
        )

        self.elements.append(new_bounds)
        return new_bounds

    def _calculate_overlap(self, bounds: ElementBounds) -> float:
        """
        Calcule le chevauchement total avec les éléments existants.
        """
        total_overlap = 0
        for element in self.elements:
            # Ajouter les marges aux calculs
            x_overlap = max(0, min(bounds.x2 + bounds.margin, element.x2 + element.margin) -
                            max(bounds.x1 - bounds.margin, element.x1 - element.margin))
            y_overlap = max(0, min(bounds.y2 + bounds.margin, element.y2 + element.margin) -
                            max(bounds.y1 - bounds.margin, element.y1 - element.margin))
            total_overlap += x_overlap * y_overlap
        return total_overlap

    def get_adjusted_positions(self) -> List[ElementBounds]:
        """
        Retourne la liste des éléments avec leurs positions ajustées.
        """
        return self.elements