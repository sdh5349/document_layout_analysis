#!/usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import numpy as np
import cv2

import pdfplumber
import fitz

def load_image(image_path):

    # initialization
    image = None

    # read image (only JPEG and PNG formats are supported currently) (20230815)
    name = image_path.lower()
    if name.endswith('.jpg') or name.endswith('.png'):
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)

    return image

def load_pdf(pdf_path, page_index = 0):

    # initialization
    image = None

    # read PDF file
    name = pdf_path.lower()
    if name.endswith('.pdf'):
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            if page_index >= page_count - 1:
                page_index = page_count - 1

            page = pdf.pages[page_index]  # select the specified page (the first page will be chosen, by default)
            page_image = page.to_image(resolution=150) # convert the page to image by default (20230815)
            image = cv2.cvtColor(np.array(page_image.original), cv2.COLOR_RGB2BGR)

            pdf.close()

    return image

def load_whole_pdf(pdf_path):

    # initialization
    image_list = []

    # read PDF file (load all pages in the PDF file)
    name = pdf_path.lower()
    if name.endswith('.pdf'):
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for page_index in range(page_count):  # traverse all pages
                page = pdf.pages[page_index]  # select the current page
                page_image = page.to_image(resolution=150) # convert the page to image by default (20230815)
                image = cv2.cvtColor(np.array(page_image.original), cv2.COLOR_RGB2BGR)

                image_list.append(image)

            pdf.close()

    return image_list

def load_document(document_path, whole_flag = False):

    # initialization
    image = None

    # load file
    name = document_path.lower()
    if name.endswith('.pdf'):
        if whole_flag is True:
            image = load_whole_pdf(document_path)
        else:
            image = load_pdf(document_path)
    else:
        image = load_image(document_path)

    return image

def load_whole_pdf_shin(pdf_path, resolution=72):
    """
    Convert all pages of a PDF to images and return both image list and page list.

    Parameters:
      pdf_path: path to the PDF file
      resolution: image resolution (default: 150 DPI)

    Return:
      image_list: list of OpenCV images of the PDF pages
      page_list: list of fitz.Page objects (for further processing if needed)
    """
    
    # initialization
    image_list = []

    # read PDF file
    name = pdf_path.lower()
    if name.endswith('.pdf'):
        pdf_document = fitz.open(pdf_path)
        page_count = len(pdf_document)

        for page_index in range(page_count):  # traverse all pages
            page = pdf_document.load_page(page_index)  # load the current page

            # Render page to an image (Pixmap object)
            zoom = resolution / 72  # adjust the resolution (72 DPI is the default)
            mat = fitz.Matrix(zoom, zoom)  # create transformation matrix for zooming
            pix = page.get_pixmap(matrix=mat, alpha=False)  # convert to image, no transparency
            
            # Convert Pixmap to a format suitable for OpenCV (BGR format)
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:  # RGBA -> BGR
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:  # RGB -> BGR
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            image_list.append(image)  # add the image to the list

        pdf_document.close()
    return image_list