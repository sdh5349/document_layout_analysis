# Document Layout Analysis 



## Introduction

https://github.com/AlibabaResearch/AdvancedLiterateMachinery 레포를 이용

아래와 같이 PDF문서(Readable)가 들어왔을 경우  HTML 형태로 변경



- Sample

![sample](https://github.com/sdh5349/document_layout_analysis/blob/main/images/1.png)









## Installation

### 1. Package Install

```
pip install -r requirements.txt
```

### 2. Model Weight Download

```
wget -c -t 100 -P /home/ https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.2.0-docX-release/DocXLayout_231012.pth
wget -c -t 100 -P /home/ https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.6.0-LaTeX-OCR-models/LaTeX-OCR_image_resizer.onnx
wget -c -t 100 -P /home/ https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.6.0-LaTeX-OCR-models/LaTeX-OCR_encoder.onnx
wget -c -t 100 -P /home/ https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.6.0-LaTeX-OCR-models/LaTeX-OCR_decoder.onnx
wget -c -t 100 -P /home/ https://github.com/AlibabaResearch/AdvancedLiterateMachinery/releases/download/v1.6.0-LaTeX-OCR-models/LaTeX-OCR_tokenizer.json

```



## Inference

### 1. Move Directory

```
cd Applications/DocXChain/
```

### 2. Inference

```
python example.py pdf2html sample.pdf sample.png
```

