import gradio as gr
from PIL import Image
import fitz  # PyMuPDF
import io
import os
from typing import Dict, List, Tuple
import torch
from transformers import pipeline


class BasicPDFExtractor:
    def __init__(self):
        """
        Initialize a basic PDF extractor with minimal dependencies.
        The model will be loaded only when needed to prevent connection issues.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.image_captioner = None

    def _ensure_image_captioner(self):
        """
        Lazy loading of the image captioning model.
        Only loads when first needed to prevent startup issues.
        """
        if self.image_captioner is None:
            try:
                print("Loading image captioning model...")
                # Using a smaller model for initial testing
                self.image_captioner = pipeline(
                    "image-to-text",
                    model="Salesforce/blip-image-captioning-base",
                    device=self.device
                )
                print("Model loaded successfully!")
            except Exception as e:
                print(f"Error loading model: {str(e)}")
                return False
        return True

    def extract_from_pdf(self, pdf_path: str, output_dir: str) -> List[Dict]:
        """
        Extract images and text from a PDF file with basic error handling

        Args:
            pdf_path: Path to the PDF file
            output_dir: Directory to save extracted images

        Returns:
            List of dictionaries containing extracted data
        """
        os.makedirs(output_dir, exist_ok=True)
        extracted_data = []

        try:
            # Open PDF with proper error handling
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"Error opening PDF: {str(e)}")
            return extracted_data

        base_name = os.path.basename(pdf_path).split('.')[0]

        try:
            for page_num in range(doc.page_count):
                print(f"Processing page {page_num + 1} of {doc.page_count}")

                try:
                    page = doc.load_page(page_num)

                    # Extract text from page
                    text = page.get_text()

                    # Extract images from page
                    image_list = page.get_images()

                    for img_idx, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]

                            # Convert to PIL Image
                            image = Image.open(io.BytesIO(image_bytes))

                            # Save image
                            image_filename = f"{base_name}_page{page_num + 1}_img{img_idx}.png"
                            image_path = os.path.join(output_dir, image_filename)
                            image.save(image_path)

                            # Generate caption if model is available
                            caption = "Image caption not available"
                            if self._ensure_image_captioner():
                                try:
                                    result = self.image_captioner(image)
                                    caption = result[0]['generated_text']
                                except Exception as e:
                                    print(f"Caption generation failed: {str(e)}")

                            # Store extracted data
                            extracted_data.append({
                                'image_path': image_path,
                                'caption': caption,
                                'page_text': text[:500],  # First 500 chars for context
                                'page_num': page_num + 1
                            })

                            print(f"Successfully processed image {img_idx + 1} from page {page_num + 1}")

                        except Exception as e:
                            print(f"Error processing image {img_idx} on page {page_num + 1}: {str(e)}")
                            continue

                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {str(e)}")
                    continue

        finally:
            # Ensure document is closed even if errors occur
            doc.close()

        return extracted_data


def process_pdf(file_path: str, query: str = None) -> Tuple[str, Image.Image]:
    """
    Process a PDF file and search for relevant content
    """
    try:
        extractor = BasicPDFExtractor()
        output_dir = "uploads/markdown/images"

        print("Starting PDF processing...")
        results = extractor.extract_from_pdf(file_path, output_dir)

        if not results:
            return "No images or text extracted from PDF", None

        if query:
            # Simple search implementation
            best_match = None
            highest_score = -1

            for result in results:
                # Calculate simple matching score
                score = sum(
                    word.lower() in (result['caption'] + result['page_text']).lower()
                    for word in query.split()
                )
                if score > highest_score:
                    highest_score = score
                    best_match = result

            if best_match:
                return (
                    f"Page {best_match['page_num']}\nCaption: {best_match['caption']}\n\n"
                    f"Context: {best_match['page_text']}",
                    Image.open(best_match['image_path'])
                )

        # If no query or no match, return first result
        first_result = results[0]
        return (
            f"Page {first_result['page_num']}\nCaption: {first_result['caption']}\n\n"
            f"Context: {first_result['page_text']}",
            Image.open(first_result['image_path'])
        )

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return f"An error occurred: {str(e)}", None


# Gradio Interface
def create_interface():
    iface = gr.Interface(
        fn=process_pdf,
        inputs=[
            gr.File(label="PDF File"),
            gr.Textbox(label="Search Query (optional)")
        ],
        outputs=[
            gr.Textbox(label="Extracted Text and Caption"),
            gr.Image(type="pil", label="Extracted Image")
        ],
        title="Basic PDF Extractor",
        description="Upload a PDF to extract images and text. Image captioning will be attempted if possible."
    )
    return iface


if __name__ == "__main__":
    print("Starting application...")
    interface = create_interface()
    interface.launch()