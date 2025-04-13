# backend/app/services/dynamicLayoutManager.py
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import numpy as np
from backend.app.models.data_models import ElementType, LayoutElement


@dataclass
class GridCell:
    is_occupied: bool
    element_id: Optional[str] = None
    heat_value: float = 0.0


class DynamicLayoutManager:
    def __init__(self, page_width: float, page_height: float, grid_size: int = 20):
        """
        Initialise le gestionnaire de mise en page dynamique.

        Args:
            page_width: Largeur de la page en points
            page_height: Hauteur de la page en points
            grid_size: Nombre de cellules pour la grille (plus élevé = plus précis)
        """
        self.page_width = page_width
        self.page_height = page_height
        self.grid_size = grid_size

        # Création de la grille
        self.cell_width = page_width / grid_size
        self.cell_height = page_height / grid_size
        self.grid = self._initialize_grid()
        self.heat_map = np.zeros((grid_size, grid_size))

    def _initialize_grid(self) -> List[List[GridCell]]:
        """Initialise la grille vide."""
        return [[GridCell(is_occupied=False)
                 for _ in range(self.grid_size)]
                for _ in range(self.grid_size)]

    def _convert_to_grid_coordinates(self, bbox: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        """Convertit les coordonnées PDF en coordonnées de grille."""
        x1 = int(bbox[0] / self.cell_width)
        y1 = int(bbox[1] / self.cell_height)
        x2 = int(bbox[2] / self.cell_width) + 1
        y2 = int(bbox[3] / self.cell_height) + 1

        return (
            max(0, min(x1, self.grid_size - 1)),
            max(0, min(y1, self.grid_size - 1)),
            max(0, min(x2, self.grid_size)),
            max(0, min(y2, self.grid_size))
        )

    def _update_heat_map(self, bbox: Tuple[float, float, float, float], value: float = 1.0):
        """Met à jour la carte thermique avec la nouvelle occupation."""
        grid_coords = self._convert_to_grid_coordinates(bbox)
        x1, y1, x2, y2 = grid_coords

        # Ajout de chaleur avec décroissance gaussienne
        for i in range(max(0, x1 - 2), min(self.grid_size, x2 + 2)):
            for j in range(max(0, y1 - 2), min(self.grid_size, y2 + 2)):
                distance = np.sqrt((i - (x1 + x2) / 2) ** 2 + (j - (y1 + y2) / 2) ** 2)
                heat_value = value * np.exp(-distance / 2)
                self.heat_map[j, i] += heat_value

    def find_optimal_position(self, element: LayoutElement) -> Tuple[float, float, float, float]:
        """
        Trouve la position optimale pour un élément en utilisant la carte thermique.

        Args:
            element: Élément à positionner

        Returns:
            Tuple contenant les nouvelles coordonnées (x1, y1, x2, y2)
        """
        original_bbox = element.bbox
        element_width = original_bbox[2] - original_bbox[0]
        element_height = original_bbox[3] - original_bbox[1]

        grid_width = int(element_width / self.cell_width) + 1
        grid_height = int(element_height / self.cell_height) + 1

        best_score = float('inf')
        best_position = original_bbox

        # Recherche de la meilleure position
        for i in range(self.grid_size - grid_width):
            for j in range(self.grid_size - grid_height):
                # Calcul du score basé sur la chaleur
                area_heat = np.sum(self.heat_map[j:j + grid_height, i:i + grid_width])

                # Pénalité pour l'éloignement de la position originale
                original_pos = self._convert_to_grid_coordinates(original_bbox)
                distance_penalty = np.sqrt((i - original_pos[0]) ** 2 + (j - original_pos[1]) ** 2)

                score = area_heat + distance_penalty * 0.5

                if score < best_score:
                    best_score = score
                    best_position = (
                        i * self.cell_width,
                        j * self.cell_height,
                        (i + grid_width) * self.cell_width,
                        (j + grid_height) * self.cell_height
                    )

        return best_position

    @staticmethod
    def _adjust_element_size(element: LayoutElement, available_space: float) -> Tuple[float, float]:
        """
        Ajuste la taille d'un élément en fonction de l'espace disponible.

        Args:
            element: Élément à redimensionner
            available_space: Espace disponible en points

        Returns:
            Tuple (nouvelle_largeur, nouvelle_hauteur)
        """
        if element.element_type != ElementType.IMAGE:
            return element.size

        original_width, original_height = element.size
        aspect_ratio = original_width / original_height

        # Calcul de la nouvelle taille en préservant le ratio
        new_width = min(original_width, available_space)
        new_height = new_width / aspect_ratio

        return new_width, new_height

    def organize_layout(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """
        Organise les éléments sur la page en évitant les chevauchements.

        Args:
            elements: Liste des éléments à organiser

        Returns:
            Liste des éléments avec leurs nouvelles positions
        """
        # Trier les éléments par priorité et taille
        sorted_elements = sorted(
            elements,
            key=lambda e: (e.priority.value, (e.bbox[2] - e.bbox[0]) * (e.bbox[3] - e.bbox[1])),
            reverse=True
        )

        organized_elements = []

        for element in sorted_elements:
            # Trouver la position optimale
            new_bbox = self.find_optimal_position(element)

            # Calculer l'espace disponible
            available_width = new_bbox[2] - new_bbox[0]

            # Ajuster la taille si nécessaire
            new_width, new_height = self._adjust_element_size(element, available_width)

            # Créer un nouvel élément avec la position et taille ajustées
            new_element = LayoutElement(
                content=element.content,
                element_type=element.element_type,
                bbox=new_bbox,
                priority=element.priority,
                size=(new_width, new_height),
                original_position=element.original_position,
                relationships=element.relationships,
                font_size=element.font_size,
                font_name=element.font_name,
                font_weight=element.font_weight,
                text_alignment=element.text_alignment,
                line_height=element.line_height,
                rotation=element.rotation,
                color=element.color,
                page_number=element.page_number
            )

            # Mettre à jour la carte thermique
            self._update_heat_map(new_bbox)

            organized_elements.append(new_element)

        return organized_elements