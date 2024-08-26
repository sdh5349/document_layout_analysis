import fitz  # PyMuPDF
import numpy as np

from modules.layout_analysis import LayoutAnalysis
from modules.table_structure_recognition import TableStructureRecognition
from modules.formula_recognition import FormulaRecognition

class Document2Html(object):
    def __init__(self, configs):
        """
        Initialize the class instance.
        """
        self.layout_analysis_module = LayoutAnalysis(configs['layout_analysis_configs'])
        self.text_detection_module = self.text_detection_and_recognition  # Use PyMuPDF for detection and recognition
        self.text_recognition_module = self.text_detection_and_recognition  # Use PyMuPDF for detection and recognition
        self.formula_recognition_module = FormulaRecognition(configs['formula_recognition_configs'])

    def __call__(self, image, page):
        """
        Process the PDF document (layout analysis + content recognition).

        Parameters:
          image: image of the PDF page.
          page: the fitz.Page object for the corresponding PDF page.

        Return:
          final_result: final document structurization result in HTML-like format.
        """
        final_result = []

        # Perform layout analysis
        la_result = self.layout_analysis_module(image)
        # Perform text detection and recognition on the page
        det_result, rec_result = self.text_detection_module(page)

        # Combine the results to produce the final output
        final_result = self._assemble(page, la_result, det_result, rec_result)

        return final_result

    def text_detection_and_recognition(self, page):
        """
        Use PyMuPDF to detect and recognize text in the PDF page.

        Parameters:
          page: a loaded PyMuPDF page object.

        Return:
          det_result: detected text boxes.
          rec_result: recognized text contents with font size and indent.
        """
        text_info = page.get_text("dict")  # Extract text and position data as a dictionary
        det_result = []
        rec_result = []

        for block in text_info["blocks"]:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]  # Recognized text
                    bbox = span["bbox"]  # Text bounding box (coordinates)
                    font_size = span["size"]  # Font size
                    indent = span["origin"][0]  # Horizontal position to calculate indent
                    det_result.append(bbox)
                    rec_result.append({
                        "text": text,
                        "font_size": font_size,
                        "indent": indent
                    })

        return np.array(det_result), np.array(rec_result)
    
    def _get_overlap_area(self, bbox, layout_box):
        """
        Calculate the overlapping area between bbox and layout_box.
        
        Parameters:
        bbox: Bounding box as [x_min, y_min, x_max, y_max].
        layout_box: Layout box as [x_min, y_min, x_max, y_max].
        
        Return:
        The overlapping area between the two boxes.
        """
        # Find the coordinates of the intersection rectangle
        x_min = max(bbox[0], layout_box[0][0])
        y_min = max(bbox[1], layout_box[0][1])
        x_max = min(bbox[2], layout_box[2][0])
        y_max = min(bbox[3], layout_box[2][1])

        # Calculate the width and height of the overlap area
        overlap_width = max(0, x_max - x_min)
        overlap_height = max(0, y_max - y_min)

        # Return the overlap area
        return overlap_width * overlap_height

    def _is_box_inside(self, bbox, layout_box, threshold=0.4):
        """
        Check if bbox is inside layout_box based on an overlap percentage threshold.

        Parameters:
        bbox: Bounding box as [x_min, y_min, x_max, y_max].
        layout_box: Layout box as [x_min, y_min, x_max, y_max].
        threshold: The minimum percentage of the bbox that must be inside layout_box (default is 50%).

        Return:
        True if the overlapping area between bbox and layout_box is greater than the threshold, False otherwise.
        """
        # Calculate the areas of bbox and the overlapping area
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        overlap_area = self._get_overlap_area(bbox, layout_box)

        # Calculate the overlap percentage
        overlap_percentage = overlap_area / bbox_area if bbox_area > 0 else 0

        # Return True if the overlap percentage is greater than or equal to the threshold
        return overlap_percentage >= threshold


    def _assemble(self, page, la_result, det_result, rec_result):
        """
        Assemble the layout and text recognition results in HTML-like format.

        Parameters:
          page: the PDF page.
          la_result: layout analysis result.
          det_result: text detection result (bounding boxes).
          rec_result: text recognition result (recognized text with font size and indent).

        Return:
          output: final result with structured text data in HTML-like format.
        """
        output = []
        layout_dets = la_result['layout_dets']

        html_output = ""

        for i in range(len(layout_dets)):
            category_index = layout_dets[i]['category_id']
            category_name = self.layout_analysis_module.mapping(category_index)
            layout_box = [(layout_dets[i]['poly'][0], layout_dets[i]['poly'][1]),\
                          (layout_dets[i]['poly'][2], layout_dets[i]['poly'][3]),\
                          (layout_dets[i]['poly'][4], layout_dets[i]['poly'][5]),\
                          (layout_dets[i]['poly'][6], layout_dets[i]['poly'][7])]
            
            region_poly = np.array([round(layout_box[0][0]), round(layout_box[0][1]),\
                            round(layout_box[1][0]), round(layout_box[1][1]),\
                            round(layout_box[2][0]), round(layout_box[2][1]),\
                            round(layout_box[3][0]), round(layout_box[3][1])])

            # Create a block for each category
            html_output += f"<{category_name} id=entity_{i}>\n"

            layout_region = {}
            layout_region['category_index'] = category_index
            layout_region['category_name'] = category_name
            layout_region['region_poly'] = region_poly.tolist()
            layout_region['text_list'] = []  # one region may contain multiple text instances
            if category_name == 'equation':
                # Handle formulas
                formula_recognition = self.formula_recognition_module(page, layout_box)
                html_output += f"  $$ {formula_recognition} $$\n"
            else:
                for j in range(len(det_result)):
                    bbox = det_result[j]
                    if not self._is_box_inside(bbox, layout_box):
                        continue
                    text_content = rec_result[j]['text']
                    font_size = rec_result[j]['font_size']
                    indent = rec_result[j]['indent']

                    # Convert the indent and font size to a more readable form
                    indent_level = f"{indent:.2f}px"
                    font_size_value = f"{font_size:.2f}px"

                    # HTML-like output for the text
                    html_output += f"  <span style='font-size:{font_size_value}; text-indent:{indent_level};'>{text_content}</span>\n"

            html_output += f"</{category_name}>\n"
            output.append(layout_region)
        return html_output, output

    def release(self):
        """
        Release resources.
        """
        if self.layout_analysis_module is not None:
            self.layout_analysis_module.release()

        if self.formula_recognition_module is not None:
            self.formula_recognition_module.release()

        return
