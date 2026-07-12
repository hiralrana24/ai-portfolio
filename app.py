import streamlit as st
import fitz
import base64
import json
import pandas as pd
from mistralai.client import Mistral

# Your API key
API_KEY = "s46f3EZ1Up9LrY0INTDQ8wyGMSYggC05"

def extract_image_from_pdf(pdf_bytes, zoom=3):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

def extract_invoice_data(image_bytes, api_key):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    client = Mistral(api_key=api_key)
    response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract ONLY visible data from this invoice. Respond ONLY in JSON: {\"invoice_number\": \"\", \"date\": \"\", \"supplier\": \"\", \"total_ht\": 0.0, \"total_tva\": 0.0, \"total_ttc\": 0.0}"
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:image/png;base64,{base64_image}"
                    }
                ]
            }
        ]
    )
    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)

def save_to_excel(data, output_path="invoices_output.xlsx"):
    try:
        existing_df = pd.read_excel(output_path)
        new_df = pd.DataFrame([data])
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
    except FileNotFoundError:
        final_df = pd.DataFrame([data])
    final_df.to_excel(output_path, index=False)
    return final_df

# --- STREAMLIT INTERFACE ---
st.title("🏨 Hotel Invoice Extractor")
st.write("Upload an invoice PDF and let AI extract the data automatically!")

uploaded_file = st.file_uploader("Upload your invoice (PDF)", type="pdf")

if uploaded_file:
    st.info("Processing your invoice...")
    
    pdf_bytes = uploaded_file.read()
    image_bytes = extract_image_from_pdf(pdf_bytes)
    
    st.image(image_bytes, caption="Invoice preview", width=400)
    
    with st.spinner("AI is reading your invoice..."):
        data = extract_invoice_data(image_bytes, API_KEY)
    
    st.success("✅ Data extracted successfully!")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total HT", f"{data['total_ht']}€")
    col2.metric("Total TVA", f"{data['total_tva']}€")
    col3.metric("Total TTC", f"{data['total_ttc']}€")
    
    st.write("### Invoice Details")
    st.json(data)
    
    df = save_to_excel(data)
    st.write("### All Invoices")
    st.dataframe(df)
    
    st.download_button(
        label="📥 Download Excel",
        data=open("invoices_output.xlsx", "rb").read(),
        file_name="invoices_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )