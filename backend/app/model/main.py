# Model/main.py

import copy
import math
import re
from pathlib import Path
from typing import List, Tuple, Union
import matplotlib.pyplot as plt
import numpy as np
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from backend.app.utils.textwrap_japanese import fw_fill_ja
from backend.app.utils.textwrap_vietnamese import fw_fill_vi
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_Weights
from torchvision.transforms import transforms
import torch
import random
import cv2
import os
import fitz
import easyocr

seed = 1234
random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

CATEGORIES2LABELS = {
    0: "bg",
    1: "text",
    2: "title",
    3: "list",
    4: "table",
    5: "figure"
}
MODEL_PATH = os.path.join(os.getcwd(), "model_196000.pth")


def get_instance_segmentation_model(num_classes):
    '''
    Cette fonction retourne un modèle Mask R-CNN avec un backbone ResNet-50-FPN.
    Le modèle est pré-entraîné sur le dataset PubLayNet.
    -----
    Input:
        num_classes: nombre de classes
    Output:
        model: modèle Mask R-CNN avec un backbone ResNet-50-FPN
    '''
    model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256

    model.roi_heads.mask_predictor = MaskRCNNPredictor(
        in_features_mask,
        hidden_layer,
        num_classes
    )
    return model


class TranslationLayoutRecovery:
    """TranslationLayoutRecovery class.

    Attributs from _load_init()
    ----------
    font: ImageFont
        Font for drawing text on the image
    ocr_model: EasyOCR
        OCR model for detecting text in the text blocks
    translate_model:
        Translation model for translating text
    translate_tokenizer:
        Tokenizer for decoding the output of the translation model
    """
    DPI = 300
    FONT_SIZE_VIETNAMESE = 34
    FONT_SIZE_JAPANESE = 28

    def __init__(self):
        self._load_init()

    def _repeated_substring(self, s: str):
        """Vérifie la présence de sous-chaînes répétées qui pourraient indiquer une erreur de traduction."""
        n = len(s)
        for i in range(10, n // 2 + 1):
            pattern = s[:i]
            matches = [match for match in re.finditer(rf'\b{re.escape(pattern)}\b', s)]
            if len(matches) >= 15:
                return True
        for i in range(n // 2 + 11, n):
            pattern = s[n // 2 + 1:i]
            matches = [match for match in re.finditer(rf'\b{re.escape(pattern)}\b', s)]
            if len(matches) >= 15:
                return True
        return False

    def translate_pdf(self, input_path: Union[Path, bytes], language: str, output_path: Path, merge: bool) -> None:
        """Fonction principale pour traduire des fichiers PDF.

        La traduction est effectuée selon les étapes suivantes:
            1. Convertir le fichier PDF en images
            2. Détecter les blocs de texte dans les images
            3. Pour chaque bloc de texte, détecter le texte et le traduire
            4. Dessiner le texte traduit sur l'image
            5. Sauvegarder l'image en fichier PDF
            6. Fusionner tous les fichiers PDF en un seul

        À l'étape 3, cette fonction ne traduit pas le texte après
        la section références. Au lieu de cela, elle sauvegarde l'image telle quelle.

        Parameters
        ----------
        input_path: Union[Path, bytes]
            Path to the input PDF file or bytes of the input PDF file
        output_path: Path
            Path to the output directory
        """
        pdf_images = convert_from_path(input_path, dpi=self.DPI)
        print("Language:", language)
        self.language = language
        pdf_files = []
        reached_references = False

        # Batch
        idx = 0
        file_id = 0
        batch_size = 8
        for _ in tqdm(range(math.ceil(len(pdf_images) / batch_size))):
            image_list = pdf_images[idx:idx + batch_size]
            if not reached_references:
                image_list, reached_references = self._translate_multiple_pages(
                    image_list=image_list,
                    reached_references=reached_references,
                )
                if merge:
                    # merge original and translated images into 1 page
                    for _, [translated_image, original_image] in enumerate(image_list):
                        saved_output_path = os.path.join(output_path, f"{file_id:03}.pdf")
                        fig, ax = plt.subplots(1, 2, figsize=(20, 14))
                        ax[0].imshow(original_image)
                        ax[1].imshow(translated_image)
                        ax[0].axis("off")
                        ax[1].axis("off")
                        plt.tight_layout()
                        plt.savefig(saved_output_path, format="pdf", dpi=self.DPI)
                        plt.close(fig)
                        pdf_files.append(saved_output_path)
                        file_id += 1
                else:
                    # convert image to pdf
                    for _, [translated_image, _] in enumerate(image_list):
                        saved_output_path = os.path.join(output_path, f"{file_id:03}.pdf")
                        pil_image = Image.fromarray(translated_image)
                        pil_image = pil_image.convert("RGB")
                        pil_image.save(saved_output_path)
                        pdf_files.append(saved_output_path)
                        file_id += 1
            idx += batch_size

        self._merge_pdfs(pdf_files)

    def _load_init(self):
        """Fonction qui charge les modèles nécessaires pour la traduction."""
        # Chargement des polices
        self.font_ja = ImageFont.truetype(
            "C:\\Users\\herve\\OneDrive - Universite de Montreal\\Github\\Axo\\backend\\fonts\\Source Han Serif CN Light.otf",
            size=self.FONT_SIZE_JAPANESE,
        )
        self.font_vi = ImageFont.truetype(
            "C:\\Users\\herve\\OneDrive - Universite de Montreal\\Github\\Axo\\backend\\fonts\\AlegreyaSans-Regular.otf",
            size=self.FONT_SIZE_VIETNAMESE,
        )

        # Modèle de détection: PubLayNet
        self.num_classes = len(CATEGORIES2LABELS.keys())
        self.pub_model = get_instance_segmentation_model(self.num_classes)

        # Chargement des poids du modèle
        if os.path.exists("C:\\Users\\herve\\OneDrive - Universite de Montreal\\Github\\Axo\\backend\\models\\model_196000.pth"):
            self.checkpoint_path = "C:\\Users\\herve\\OneDrive - Universite de Montreal\\Github\\Axo\\backend\\models\\model_196000.pth"
        else:
            raise Exception("Model weights not found.")

        assert os.path.exists(self.checkpoint_path)

        import argparse
        import torch.serialization
        # Avant le chargement du modèle:
        torch.serialization.add_safe_globals([argparse.Namespace])

        # Puis garder la ligne d'origine:
        checkpoint = torch.load(self.checkpoint_path, map_location='cpu')
        self.pub_model.load_state_dict(checkpoint['model'])
        self.pub_model = self.pub_model.to("cuda")
        self.pub_model.eval()

        # Modèle d'OCR: EasyOCR
        self.ocr_model = easyocr.Reader(['en'], gpu=True)

        # Modèles de traduction
        self.translate_model_ja = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-en-jap").to("cuda")
        self.translate_tokenizer_ja = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-jap")

        self.translate_model_vi = AutoModelForSeq2SeqLM.from_pretrained("VietAI/envit5-translation").to("cuda")
        self.translate_tokenizer_vi = AutoTokenizer.from_pretrained("VietAI/envit5-translation")

        # Transformation pour le modèle
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.ToTensor()
        ])

    def _crop_img(self, box, ori_img):
        """Découpe une partie d'image selon les coordonnées d'une boîte"""
        new_box_0 = int(box[0] / self.rat) - 20
        new_box_1 = int(box[1] / self.rat) - 10
        new_box_2 = int(box[2] / self.rat) + 20
        new_box_3 = int(box[3] / self.rat) + 10
        temp_img = ori_img[new_box_1:new_box_3, new_box_0:new_box_2]
        box = [new_box_0, new_box_1, new_box_2, new_box_3]
        return temp_img, box

    def _ocr_module(self, list_boxes, list_labels_idx, ori_img):
        """Module principal qui fait l'OCR sur chaque bloc et remplace le texte par sa traduction"""
        original_image = copy.deepcopy(ori_img)
        list_labels = list(map(lambda y: CATEGORIES2LABELS[y.item()], list_labels_idx))
        list_masks = list(map(lambda x: x == "text", list_labels))
        list_boxes_filtered = list_boxes[list_masks]
        list_images_filtered = [original_image] * len(list_boxes_filtered)

        results = list(map(self._crop_img, list_boxes_filtered, list_images_filtered))

        if len(results) > 0:
            list_temp_images, list_new_boxes = [row[0] for row in results], [row[1] for row in results]

            list_ocr_results = list(map(lambda x: np.array(x, dtype=object)[:, 1] if len(x) > 0 else None,
                                        list(map(lambda x: self.ocr_model.readtext(x), list_temp_images))))

            for ocr_results, box in zip(list_ocr_results, list_new_boxes):
                if ocr_results is not None:
                    ocr_text = " ".join(ocr_results)
                    if len(ocr_text) > 1:
                        text = re.sub(r"\n|\t|\[|\]|\/|\|", " ", ocr_text)
                        translated_text = self._translate(text)
                        translated_text = re.sub(r"\n|\t|\[|\]|\/|\|", " ", translated_text)

                        # Si la plupart des caractères ne sont pas japonais, on ignore la traduction
                        if self.language == "ja":
                            if len(
                                    re.findall(
                                        r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]",
                                        translated_text,
                                    )
                            ) > 0.8 * len(translated_text):
                                print("skipped")
                                continue

                        # Pour VietAI/envit5-translation, remplacer "vi"
                        if self.language == "vi":
                            translated_text = translated_text.replace("vi: ", "")
                            translated_text = translated_text.replace("vi ", "")
                            translated_text = translated_text.strip()

                        if self.language == "ja":
                            if self._repeated_substring(translated_text):  # Vérifier les sous-chaînes répétées
                                processed_text = fw_fill_ja(
                                    text,
                                    width=int(
                                        (box[2] - box[0]) / (self.FONT_SIZE_JAPANESE / 2)
                                    )
                                          + 1,
                                )
                            else:
                                processed_text = fw_fill_ja(
                                    translated_text,
                                    width=int(
                                        (box[2] - box[0]) / (self.FONT_SIZE_JAPANESE / 2)
                                    )
                                          + 1,
                                )
                        else:
                            if self._repeated_substring(translated_text):
                                processed_text = fw_fill_vi(
                                    text,
                                    width=int(
                                        (box[2] - box[0]) / (self.FONT_SIZE_VIETNAMESE / 2)
                                    )
                                          + 1,
                                )
                            else:
                                processed_text = fw_fill_vi(
                                    translated_text,
                                    width=int(
                                        (box[2] - box[0]) / (self.FONT_SIZE_VIETNAMESE / 2)
                                    )
                                          + 1,
                                )

                        # Création d'un nouveau bloc pour le texte traduit
                        new_block = Image.new(
                            "RGB",
                            (
                                box[2] - box[0],
                                box[3] - box[1],
                            ),
                            color=(255, 255, 255),
                        )
                        draw = ImageDraw.Draw(new_block)
                        if self.language == "ja":
                            draw.text(
                                (0, 0),
                                text=processed_text,
                                font=self.font_ja,
                                fill=(0, 0, 0),
                            )
                        else:
                            draw.text(
                                (0, 0),
                                text=processed_text,
                                font=self.font_vi,
                                fill=(0, 0, 0),
                            )

                        new_block = np.array(new_block)
                        original_image[
                        int(box[1]): int(box[3]),
                        int(box[0]): int(box[2]),
                        ] = new_block
                else:
                    continue

        reached_references = False

        # Vérification des titres "Reference" et "Abstract"
        list_title_masks = list(map(lambda x: x == "title", list_labels))
        list_boxes_filtered = list_boxes[list_title_masks]
        list_images_filtered = [original_image] * len(list_boxes_filtered)

        results = list(map(self._crop_img, list_boxes_filtered, list_images_filtered))
        if len(results) > 0:
            list_temp_images = [row[0] for row in results]
            list_title_ocr_results = list(map(lambda x: np.array(x, dtype=object)[:, 1] if len(x) > 0 else None,
                                              list(map(lambda x: self.ocr_model.readtext(x), list_temp_images))))
            if len(list_title_ocr_results) > 0:
                for i, (result, box) in enumerate(zip(list_title_ocr_results, list_boxes_filtered)):
                    if result is not None:
                        if result[0].lower() in ["references", "reference"]:
                            reached_references = True
                        elif result[0].lower() == "abstract":
                            # Conserver le titre et les auteurs originaux
                            new_box_1 = int(box[1] / self.rat)
                            original_image[
                            int(0): int(new_box_1),
                            int(0): int(original_image.shape[1]),
                            ] = ori_img[
                                int(0): int(new_box_1),
                                int(0): int(ori_img.shape[1]),
                                ]

        return original_image, reached_references

    def _preprocess_image(self, image):
        """Prétraitement d'une image pour le modèle Mask R-CNN"""
        ori_img = np.array(image)
        img = ori_img[:, :, ::-1].copy()

        # Redimensionnement pour maintenir un ratio constant
        self.rat = 1000 / img.shape[0]

        img = cv2.resize(img, None, fx=self.rat, fy=self.rat)
        img = self.transform(img).cuda()

        return [img, ori_img]

    def _translate_multiple_pages(
            self,
            image_list: List[Image.Image],
            reached_references: bool,
    ) -> Tuple[np.ndarray, np.ndarray, bool]:
        """Traduit une page du PDF."""
        results = list(map(self._preprocess_image, image_list))
        new_list_images, list_original_images = [row[0] for row in results], [row[1] for row in results]
        with torch.no_grad():
            predictions = self.pub_model(new_list_images)

        list_masks = list(map(lambda x: x["scores"] >= 0.7, predictions))
        new_list_boxes = list(map(lambda x, y: x['boxes'][y, :], predictions, list_masks))
        new_list_labels = list(map(lambda x, y: x["labels"][y], predictions, list_masks))

        list_returned_images = []
        reached_references = False
        for one_image_boxes, one_image_labels, original_image in zip(new_list_boxes, new_list_labels,
                                                                     list_original_images):
            one_translated_image, reached_references = self._ocr_module(one_image_boxes, one_image_labels,
                                                                        original_image)
            list_returned_images.append([one_translated_image, original_image])
            if reached_references:
                break

        return list_returned_images, reached_references

    def _translate(self, text: str) -> str:
        """Traduit le texte en utilisant le modèle de traduction approprié."""
        texts = self._split_text(text, 450)

        translated_texts = []
        for i, t in enumerate(texts):
            http_res = ("http" in t) or ("https" in t)
            if not http_res:
                if self.language == "ja":
                    inputs = self.translate_tokenizer_ja(t, return_tensors="pt").input_ids.to(
                        "cuda"
                    )
                    outputs = self.translate_model_ja.generate(inputs, max_length=512)
                    res = self.translate_tokenizer_ja.decode(outputs[0], skip_special_tokens=True)
                else:
                    inputs = self.translate_tokenizer_vi(t, return_tensors="pt").input_ids.to(
                        "cuda"
                    )
                    outputs = self.translate_model_vi.generate(inputs, max_length=512)
                    res = self.translate_tokenizer_vi.decode(outputs[0], skip_special_tokens=True)
            else:
                res = t

            # Ignorer les textes de préface japonais
            if self.language == "ja" and res.startswith("「この版"):
                continue

            translated_texts.append(res)
        return " ".join(translated_texts)

    def _split_text(self, text: str, text_limit_length: int = 448) -> List[str]:
        """Divise le texte en morceaux ne dépassant pas text_limit_length."""
        if len(text) < text_limit_length:
            return [text]

        sentences = text.rstrip().split(". ")
        sentences = [s + ". " for s in sentences[:-1]] + sentences[-1:]
        result = []
        current_text = ""
        for sentence in sentences:
            if len(current_text) + len(sentence) < text_limit_length:
                current_text += sentence
            else:
                if current_text:
                    result.append(current_text)
                while len(sentence) >= text_limit_length:
                    result.append(sentence[:text_limit_length - 1])
                    sentence = sentence[text_limit_length - 1:].lstrip()
                current_text = sentence
        if current_text:
            result.append(current_text)
        return result

    def _merge_pdfs(self, pdf_files: List[str]) -> None:
        """Fusionne les fichiers PDF traduits en un seul."""
        result = fitz.open()
        for pdf_file in sorted(pdf_files):
            with fitz.open(pdf_file) as f:
                result.insert_pdf(f)
                os.remove(pdf_file)
        result.save(os.path.join("output", "PDFs", "fitz_translated.pdf"))