import fitz  # PyMuPDF
import numpy as np

from modules.layout_analysis import LayoutAnalysis
from modules.table_structure_recognition import TableStructureRecognition
from modules.formula_recognition import FormulaRecognition
from utilities.visualization import *
class Document2Html(object):
    def __init__(self, configs):
        """
        Initialize the class instance.
        """
        self.layout_analysis_module = LayoutAnalysis(configs['layout_analysis_configs'])
        self.text_detection_module = self.text_detection_and_recognition  # Use PyMuPDF for detection and recognition
        self.text_recognition_module = self.text_detection_and_recognition  # Use PyMuPDF for detection and recognition
        self.formula_recognition_module = FormulaRecognition(configs['formula_recognition_configs'])
        self.table_structure_recognition_module = TableStructureRecognition(configs['table_structure_recognition_configs'])
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
        tsr_result = self.table_structure_recognition_module(image)
        # table_output = self._table_recognize(tsr_result, det_result, rec_result)
        final_result = self._assemble(page, la_result, det_result, rec_result, tsr_result)

        return final_result
    
    def _point_in_box(self, box, point):
        x1,y1 = box[0][0],box[0][1]
        x2,y2 = box[1][0],box[1][1]
        x3,y3 = box[2][0],box[2][1]
        x4,y4 = box[3][0],box[3][1]
        ctx,cty = point[0],point[1]
        a = (x2 - x1)*(cty - y1) - (y2 - y1)*(ctx - x1) 
        b = (x3 - x2)*(cty - y2) - (y3 - y2)*(ctx - x2) 
        c = (x4 - x3)*(cty - y3) - (y4 - y3)*(ctx - x3) 
        d = (x1 - x4)*(cty - y4) - (y1 - y4)*(ctx - x4) 
        if ((a > 0  and  b > 0  and  c > 0  and  d > 0) or (a < 0  and  b < 0  and  c < 0  and  d < 0)):
            return True
        else :
            return False

    def _table_recognize(self, layout_box, tsr_result, det_result, rec_result):
        # initialize
        output = []
        tsr_result = np.array(tsr_result).reshape([len(tsr_result), 4, 2])
        
        # First, find tsr_result (table regions) that are inside the layout_box
        filtered_tsr_result = []
        for j in range(len(tsr_result)):
            # Check if the entire tsr_result (table cell) is inside the layout_box
            cell_center_x = (tsr_result[j][0][0] + tsr_result[j][2][0]) / 2
            cell_center_y = (tsr_result[j][0][1] + tsr_result[j][2][1]) / 2
            if self._point_in_box(layout_box, [cell_center_x, cell_center_y]):
                filtered_tsr_result.append(tsr_result[j])

        # Next, match det_result (detection results) with filtered tsr_result
        for tsr in filtered_tsr_result:
            combined_text = ""  # Initialize combined text for this table cell
            cell_poly = np.array([round(tsr[0][0]), round(tsr[0][1]),
                                round(tsr[1][0]), round(tsr[1][1]),
                                round(tsr[2][0]), round(tsr[2][1]),
                                round(tsr[3][0]), round(tsr[3][1])])

            for i in range(len(det_result)):
                pts = det_result[i]
                rec_text = rec_result[i]["text"]  # pre-extracted recognition result

                p0, p1, p2, p3 = pts
                ctx = (p0 + p2) / 2.0
                cty = (p1 + p3) / 2.0

                # Check if the detected text box is inside the current tsr_result (table region)
                if not self._point_in_box(tsr, [ctx, cty]):
                    continue

                # Combine all text in the same cell
                combined_text += " " + rec_text

            # If there's any combined text, add it to the output for the table cell
            if combined_text.strip():
                item = {
                    'position': cell_poly.tolist(),  # Table cell polygon
                    'content': combined_text.strip(),  # Combined text for the table cell
                    'cell': cell_poly.tolist()  # Cell coordinates
                }
                output.append(item)

        return output


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

    def reading_sort(self, page, layout_dets):      
        # 페이지 너비의 절반을 기준으로 왼쪽 열과 오른쪽 열을 나눔
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        mid_x = page_width / 2

        # 왼쪽 열에 속하는 layout_dets와 오른쪽 열에 속하는 layout_dets로 나눔
        left_column = []
        right_column = []

        for det in layout_dets:
            # layout_dets의 첫 번째 좌표(x축)를 기준으로 열을 나눔
            x0 = det['poly'][0]
            if x0 < mid_x:
                left_column.append(det)
            else:
                right_column.append(det)

        # 왼쪽 열과 오른쪽 열을 각각 y 좌표 기준으로 위에서 아래로 정렬
        left_column_sorted = sorted(left_column, key=lambda det: det['poly'][1])
        right_column_sorted = sorted(right_column, key=lambda det: det['poly'][1])

        # 두 열을 결합하여, 왼쪽 열을 먼저 처리하고 오른쪽 열을 나중에 처리
        return left_column_sorted + right_column_sorted

    def _assemble(self, page, la_result, det_result, rec_result, tsr_result):
        output = []
        layout_dets = self.reading_sort(page, la_result['layout_dets'])

        html_output = ""

        for i in range(len(layout_dets)):
            category_index = layout_dets[i]['category_id']
            category_name = self.layout_analysis_module.mapping(category_index)
            layout_box = [(layout_dets[i]['poly'][0], layout_dets[i]['poly'][1]),
                        (layout_dets[i]['poly'][2], layout_dets[i]['poly'][3]),
                        (layout_dets[i]['poly'][4], layout_dets[i]['poly'][5]),
                        (layout_dets[i]['poly'][6], layout_dets[i]['poly'][7])]

            region_poly = np.array([round(layout_box[0][0]), round(layout_box[0][1]),
                                    round(layout_box[1][0]), round(layout_box[1][1]),
                                    round(layout_box[2][0]), round(layout_box[2][1]),
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
            elif category_name == 'table':
                # Handle tables within the layout_box
                table_output = self._table_recognize(layout_box, tsr_result, det_result, rec_result)
                for item in table_output:
                    cell_content = item['content']
                    cell_position = item['position']
                    cell_poly = item['cell']
                    html_output += f"  <div class='table-cell' style='position:absolute; left:{cell_position[0]}px; top:{cell_position[1]}px; width:{cell_position[2] - cell_position[0]}px; height:{cell_position[3] - cell_position[1]}px;'>\n"
                    html_output += f"    {cell_content}\n"
                    html_output += f"  </div>\n"
            else:
                previous_font_size = None
                combined_text = ""
                indent = None  # To keep track of the last indent value

                for j in range(len(det_result)):
                    bbox = det_result[j]
                    if not self._is_box_inside(bbox, layout_box):
                        continue
                    
                    text_content = rec_result[j]['text']
                    font_size = rec_result[j]['font_size']
                    current_indent = rec_result[j]['indent']

                    # Check if the font size is the same as the previous text
                    if previous_font_size is None or font_size != previous_font_size:
                        # If there's accumulated text, output it first
                        if combined_text:
                            font_size_value = f"{previous_font_size:.2f}px"
                            indent_level = f"{indent:.2f}px"
                            html_output += f"  <span style='font-size:{font_size_value}; text-indent:{indent_level};'>{combined_text.strip()}</span>\n"
                            combined_text = ""
                        
                        # Update the current font size and indent
                        previous_font_size = font_size
                        indent = current_indent

                    # Combine text with the same font size
                    combined_text += " " + text_content

                # Add any remaining text with the last used font size
                if combined_text:
                    font_size_value = f"{previous_font_size:.2f}px"
                    indent_level = f"{indent:.2f}px"
                    html_output += f"  <span style='font-size:{font_size_value}; text-indent:{indent_level};'>{combined_text.strip()}</span>\n"

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
