# 🏭 S&OP RAG Assistant — Safran

> AI-powered assistant that answers questions about capacity and workload data in natural language — no more manual Excel searching.

## 🎯 Problem Solved

As an S&OP analyst at Safran, I spent hours manually searching through Excel files to answer capacity questions. This RAG assistant answers any question about workload data instantly in natural language.

**Before:** Hours of manual searching in Excel files
**After:** Natural language question → instant precise answer ✅

## 🚀 Demo

1. Ask a question in natural language
2. AI searches relevant capacity data automatically
3. Get a precise answer with data sources shown

**Example questions:**

- "Which workstations are overloaded?"
- "What is the capacity of Usinage CNC for programme A350?"
- "Which programmes have attention status this week?"

## 🛠️ Tech Stack

| Tool                      | Purpose                            |
| ------------------------- | ---------------------------------- |
| **Python**                | Core language                      |
| **Mistral AI**            | LLM for generating precise answers |
| **Sentence Transformers** | Text embeddings (all-MiniLM-L6-v2) |
| **FAISS**                 | Vector similarity search           |
| **Pandas**                | Excel data processing              |
| **Streamlit**             | Interactive web interface          |

## ⚙️ RAG Architecture

S&OP Excel Data
↓
Pandas — loads and converts rows to text
↓
Sentence Transformers — creates embeddings
↓
FAISS — indexes all embeddings
↓
User asks a question
↓
FAISS — finds most relevant data rows
↓
Mistral AI — generates answer using context
↓
✅ Precise answer with sources shown

## 📊 Data Tracked

- Workstation (Poste de charge)
- Programme (A320, A350, B787)
- Week
- Capacity (hours)
- Workload (hours)
- Load rate (%)
- Status (OK / ATTENTION / SURCHARGE)

## 💡 Key Technical Concepts

**RAG (Retrieval Augmented Generation)**
Instead of training the model on S&OP data, we retrieve relevant rows at query time and provide them as context to the LLM. This ensures accurate, up-to-date answers.

**Vector Embeddings**
Each data row is converted to a 384-dimension vector. Similar meanings = similar vectors. This allows semantic search beyond simple keyword matching.

**FAISS**
Facebook AI Similarity Search — indexes millions of vectors and finds the most similar ones in milliseconds.

## 📦 Installation

```bash
git clone https://github.com/hiralrana24/ai-portfolio
cd ai-portfolio/sop-rag-assistant
python3 -m venv venv
source venv/bin/activate
pip install streamlit sentence-transformers faiss-cpu mistralai pandas openpyxl

```

▶️ Run

python create_data.py # Generate S&OP data
streamlit run app_sop.py # Launch the assistant

Add your Mistral API key in app_sop.py:

API_KEY = "your_mistral_api_key"

💡 What I Learned

RAG pipeline from scratch (embeddings → FAISS → LLM)
Vector similarity search and semantic retrieval
Applying AI to real industrial S&OP use cases
Building conversational interfaces with Streamlit

🏭 Industrial Context

Built from my 2 years experience as S&OP analyst at Safran, one of the world's largest aerospace companies. The tool addresses a real pain point in industrial capacity planning.

🔮 Future Improvements

Connect to real ERP data (SAP, SSPP)
Add multi-week capacity forecasting
Export capacity alerts automatically
Add French language support

👩‍💻 Author

Hiral Rana — CS Student | 2 years S&OP experience at Safran | Passionate about applying AI to real-world problems

GitHub | LinkedIn
