# 🏨 Hotel Invoice Extractor

> AI-powered tool that automatically extracts data from hotel invoices and exports to Excel.

## 🎯 Problem Solved

Hotel and restaurant staff spend hours manually entering invoice data into Excel spreadsheets. This tool automates the entire process in seconds.

## 🚀 Demo

Upload a PDF invoice → AI reads it → Data extracted → Excel downloaded automatically.

## 🛠️ Tech Stack

- **Python** — Core language
- **Mistral AI (Pixtral)** — Vision AI for reading scanned invoices
- **PyMuPDF** — PDF to image conversion
- **Pandas + OpenPyXL** — Excel export
- **Streamlit** — Web interface

## ⚙️ How It Works

1. User uploads a PDF invoice (even scanned/image-based)
2. PyMuPDF converts the PDF page to a high-resolution image
3. Mistral Pixtral (Vision AI) reads the invoice and extracts structured data
4. Data is saved to Excel automatically
5. User downloads the Excel report

## 📦 Installation

```bash
git clone https://github.com/hiralrana24/ai-portfolio
cd ai-portfolio
python3 -m venv venv
source venv/bin/activate
pip install streamlit pymupdf mistralai pandas openpyxl
```
