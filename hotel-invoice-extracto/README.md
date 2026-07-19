# 🏨 Hotel Invoice Extractor

> AI-powered tool that automatically extracts data from hotel invoices and exports to Excel — no more manual data entry.

## 🎯 Problem Solved

Working in a hotel, I observed staff spending hours manually entering invoice data into Excel spreadsheets every week. This tool automates the entire process in seconds using Vision AI.

**Before:** 3+ hours of manual data entry per week
**After:** 10 seconds per invoice, fully automated ✅

## 🚀 Demo

1. Upload a PDF invoice (even scanned/image-based)
2. AI reads and understands the invoice automatically
3. Structured data appears on screen instantly
4. Download the complete Excel report with one click

## 🛠️ Tech Stack

| Tool                         | Purpose                                 |
| ---------------------------- | --------------------------------------- |
| **Python**                   | Core language                           |
| **Mistral AI (Pixtral-12b)** | Vision AI for reading scanned invoices  |
| **PyMuPDF**                  | PDF to high-resolution image conversion |
| **Pandas**                   | Data manipulation and Excel export      |
| **OpenPyXL**                 | Excel file generation                   |
| **Streamlit**                | Interactive web interface               |

## ⚙️ Architecture

PDF Invoice (scanned or digital)
↓
PyMuPDF — converts PDF to HD image (zoom x3)
↓
Mistral Pixtral Vision AI — reads invoice image
↓
JSON structured extraction:
{invoice_number, date, supplier, total_ht, total_tva, total_ttc}
↓
Pandas — saves to Excel automatically
↓
✅ Excel report ready to download

## 📊 Data Extracted

- Invoice number
- Invoice date
- Supplier name
- Total HT (excl. tax)
- Total TVA (tax)
- Total TTC (incl. tax)

## 💡 Key Technical Challenges Solved

**1. Scanned PDFs**
Most real invoices are scanned images, not text-based PDFs. Solved by using Mistral's Vision AI (Pixtral) to read images directly.

**2. AI Hallucinations**
Early versions invented data. Solved by:

- Generating HD images (zoom x3 resolution)
- Using strict JSON prompt format
- Asking AI to extract ONLY visible data

**3. Structured Output**
Raw AI responses are unpredictable. Solved by forcing JSON output and cleaning markdown formatting before parsing.

## 📦 Installation

```bash
git clone https://github.com/hiralrana24/ai-portfolio
cd ai-portfolio/hotel-invoice-extracto
python3 -m venv venv
source venv/bin/activate
pip install streamlit pymupdf mistralai pandas openpyxl
```

▶️ Run

bash
streamlit run app.py
Add your Mistral API key in app.py:
python
API_KEY = "your_mistral_api_key"

💡 What I Learned

Vision AI and OCR on real scanned documents
Prompt engineering to eliminate AI hallucinations
Building end-to-end AI pipelines from scratch
Deploying production-ready ML apps with Streamlit
Handling real-world edge cases (scanned PDFs, structured extraction)

🔮 Future Improvements

Support multiple pages per invoice
Add email sending to accountant directly
Support multiple languages (French, English, Spanish)
Batch processing of multiple invoices at once

👩‍💻 Author

Hiral Rana — CS Student | 2 years S&OP experience at Safran | Passionate about applying AI to real-world problems
GitHub | LinkedIn
