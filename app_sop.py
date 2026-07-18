import streamlit as st
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from mistralai.client import Mistral

API_KEY = "s46f3EZ1Up9LrY0INTDQ8wyGMSYggC05"

def load_sop_data(file_path="safran_sop_data.xlsx"):
    """Load S&OP data from Excel"""
    df = pd.read_excel(file_path)
    # Convert each row to a text description
    documents = []
    for _, row in df.iterrows():
        doc = f"Poste: {row['Poste de charge']} | Programme: {row['Programme']} | Semaine: {row['Semaine']} | Capacité: {row['Capacité (heures)']}h | Charge: {row['Charge (heures)']}h | Taux: {row['Taux de charge (%)']}% | Statut: {row['Statut']}"
        documents.append(doc)
    return documents, df

def create_vector_store(documents):
    """Create FAISS vector store from documents"""
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(documents).astype('float32')
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, model

def search_documents(question, index, model, documents, k=3):
    """Search relevant documents"""
    q_embedding = model.encode([question]).astype('float32')
    distances, indices = index.search(q_embedding, k=k)
    return [documents[i] for i in indices[0]]

def ask_mistral(question, context, api_key):
    """Ask Mistral with context"""
    client = Mistral(api_key=api_key)
    prompt = f"""You are an S&OP expert assistant at Safran. 
Answer the question using ONLY the data provided below.
Be precise and mention specific numbers.

Data:
{context}

Question: {question}

Answer:"""
    
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- STREAMLIT INTERFACE ---
st.set_page_config(
    page_title="S&OP Assistant Safran",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 S&OP Assistant — Safran")
st.markdown("**Ask questions about capacity and workload data in natural language.**")
st.divider()

# Load data and create index
@st.cache_resource
def initialize():
    documents, df = load_sop_data()
    index, model = create_vector_store(documents)
    return documents, df, index, model

with st.spinner("Loading S&OP data..."):
    documents, df, index, model = initialize()

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 S&OP Data")
    st.dataframe(df, use_container_width=True)

with col2:
    st.subheader("🤖 Ask a Question")
    
    # Example questions
    st.markdown("**Example questions:**")
    st.markdown("- Which workstations are overloaded?")
    st.markdown("- What is the capacity of Usinage CNC?")
    st.markdown("- Which programmes have attention status?")
    
    st.divider()
    
    question = st.text_input("Your question:", placeholder="Type your question here...")
    
    if st.button("Ask", type="primary", use_container_width=True):
        if question:
            with st.spinner("Searching data and generating answer..."):
                relevant_docs = search_documents(question, index, model, documents)
                context = "\n".join(relevant_docs)
                answer = ask_mistral(question, context, API_KEY)
            
            st.success("✅ Answer:")
            st.write(answer)
            
            with st.expander("📋 Data used to answer"):
                for doc in relevant_docs:
                    st.write(f"• {doc}")
        else:
            st.warning("Please type a question first!")