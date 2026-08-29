import streamlit as st
import fitz
import base64
import json
import io
import re
from datetime import datetime
from mistralai.client import Mistral
import xlrd
from xlutils.copy import copy as xl_copy

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Hotel Invoice Extractor",
    page_icon="🏨",
    layout="wide"
)

API_KEY = st.secrets["MISTRAL_API_KEY"]

# Onglets disponibles dans le template (noms exacts des feuilles Excel)
MONTH_SHEET_MAP = {
    1: None,       # Janvier - pas d'onglet dans ce template
    2: None,       # Février - pas d'onglet dans ce template
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Jul",
    8: "Aout",
    9: "Sept",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

# Chaque bloc de paiement : (ligne d'en-tête du bloc, première ligne de donnée, dernière ligne de donnée) - 0-indexé
PAYMENT_BLOCKS = {
    "PRELEVEMENT": (2, 3, 31),
    "CHEQUES": (32, 33, 64),
    "CB": (65, 66, 98),
}

# Espèces et virement n'ont pas de bloc dédié dans ce template -> routés par défaut.
# Modifiable ici si besoin.
PAYMENT_TYPE_TO_BLOCK = {
    "PRELEVEMENT": "PRELEVEMENT",
    "PRÉLÈVEMENT": "PRELEVEMENT",
    "VIREMENT": "PRELEVEMENT",         # pas de bloc dédié -> défaut PRELEVEMENT
    "VIREMENT BANCAIRE": "PRELEVEMENT",
    "CHEQUE": "CHEQUES",
    "CHÈQUE": "CHEQUES",
    "CHEQUES": "CHEQUES",
    "CB": "CB",
    "CARTE": "CB",
    "CARTE BANCAIRE": "CB",
    "ESPECES": "CB",   # pas de bloc dédié -> défaut CB
    "ESPÈCES": "CB",
    "CASH": "CB",
}

# Colonnes du tableau (0-indexé, colonne 0 = marge vide)
COL_FOURNISSEUR = 1
COL_DATE = 2
COL_TYPE_PAIEMENT = 3
COL_N_CHEQUE = 4
COL_HT = 5
COL_TVA = 6
COL_TTC = 7
COL_CATEGORIE = {"Restaurant": 8, "Salaire": 9, "Divers": 10}


# ============================================================
# EXTRACTION IA
# ============================================================
def extract_image_from_pdf(pdf_bytes, zoom=3):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def extract_invoice_data(image_bytes, api_key):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    client = Mistral(api_key=api_key)

    prompt = """Tu es un assistant comptable pour un hôtel en France. Analyse cette facture et extrait UNIQUEMENT les données visibles.

Réponds STRICTEMENT en JSON avec ce format exact, sans aucun texte autour :
{
  "fournisseur": "nom du fournisseur",
  "date": "JJ/MM/AAAA",
  "type_paiement": "PRELEVEMENT" ou "CHEQUE" ou "CB" ou "ESPECES",
  "n_cheque": "numéro de chèque si visible, sinon chaîne vide",
  "total_ht": 0.0,
  "total_tva": 0.0,
  "total_ttc": 0.0,
  "categorie": "Restaurant" ou "Salaire" ou "Divers"
}

Règles pour "type_paiement" : regarde la case cochée dans "MODE DE RÈGLEMENT" (CHEQUE, CB, ESPECES) ou déduis PRELEVEMENT si c'est un prélèvement automatique (loyer, abonnement, assurance).

Règles pour "categorie" (classification comptable, très important) :
- "Restaurant" : produits alimentaires, boissons, matériel de cuisine, fournisseurs de restauration (ex: Sysco, Metro, Pomona, boucherie, primeur)
- "Salaire" : tout ce qui concerne le personnel, paie, charges sociales, intérim
- "Divers" : tout le reste (fournitures, entretien, énergie, assurance, travaux, etc.)

N'invente aucune donnée. Si une information n'est pas visible, mets une chaîne vide "" ou 0.0."""

    response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{base64_image}"},
                ],
            }
        ],
    )
    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def extract_pdf_page_images(pdf_bytes, zoom=2):
    """Convertit toutes les pages d'un PDF en images PNG (pour les relevés multi-pages)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    return images


def extract_bank_transactions_from_page(image_bytes, api_key):
    """
    Analyse une page de relevé de compte bancaire et retourne la liste des
    transactions DEBIT de type CB / VIREMENT / PRELEVEMENT (hors commissions).
    """
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    client = Mistral(api_key=api_key)

    prompt = """Tu es un assistant comptable. Voici une page d'un relevé de compte bancaire.
Le tableau a 5 colonnes : DATE COMPTABLE, NATURE DES OPERATIONS, DATE DE VALEUR, DEBIT, CREDIT.

Extrait UNIQUEMENT les lignes qui remplissent TOUTES ces conditions :
1. Le montant se trouve dans la colonne DEBIT (jamais CREDIT).
2. La nature de l'opération correspond à l'un de ces 3 types :
   - CB : paiement par carte bancaire (ex: "FACTURE CARTE DU ...")
   - VIREMENT : virement SEPA émis (ex: "VIREMENT SEPA EMIS ...")
   - PRELEVEMENT : prélèvement SEPA (ex: "PRLV SEPA ...")
3. Exclut TOUTES les lignes de commissions, frais, intérêts (ex: "COMMISSIONS PERCUES...", "INTERETS ET COMMISSIONS", "COMMISSIONS FACTURE...") et toute ligne de remboursement (ex: "REMB. FACT...") ou toute ligne qui ne correspond à aucun des 3 types ci-dessus.

Réponds STRICTEMENT en JSON, sous forme de liste, sans aucun texte autour :
[
  {
    "date": "JJ/MM/AAAA",
    "description": "résumé court (bénéficiaire ou motif de l'opération)",
    "montant": 0.0,
    "type": "CB" ou "VIREMENT" ou "PRELEVEMENT",
    "categorie": "Restaurant" ou "Salaire" ou "Divers"
  }
]

Si aucune ligne ne correspond sur cette page, réponds exactement : []

Règles pour "categorie" :
- "Restaurant" : fournisseurs alimentaires, boissons, matériel de cuisine (ex: Sysco, Cafés Folliet, Metro)
- "Salaire" : tout ce qui mentionne un salaire ou des charges sociales de personnel
- "Divers" : tout le reste (énergie, assurances, impôts, abonnements, travaux, maintenance, etc.)

N'invente aucune donnée."""

    response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{base64_image}"},
                ],
            }
        ],
    )
    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return []


# ============================================================
# ECRITURE DANS LE TEMPLATE EXCEL (préserve la mise en forme .xls)
# ============================================================
def get_target_sheet_name(date_str):
    """Déduit l'onglet (mois) à partir d'une date JJ/MM/AAAA."""
    d = parse_date(date_str)
    if d is None:
        return None
    return MONTH_SHEET_MAP.get(d.month)


def parse_date(date_str):
    """Parse une date en plusieurs formats possibles. Retourne un datetime ou None."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def read_block_rows(rs, start_row, end_row):
    """Lit toutes les lignes déjà remplies d'un bloc, sous forme de liste de dicts."""
    rows = []
    for row in range(start_row, end_row + 1):
        fournisseur = rs.cell_value(row, COL_FOURNISSEUR)
        if fournisseur in (None, ""):
            continue
        categorie = "Divers"
        for cat_name, col in COL_CATEGORIE.items():
            cell_val = str(rs.cell_value(row, col)).strip().upper()
            if cell_val == "OUI":
                categorie = cat_name
                break
        rows.append({
            "fournisseur": fournisseur,
            "date": rs.cell_value(row, COL_DATE),
            "type_paiement": rs.cell_value(row, COL_TYPE_PAIEMENT),
            "n_cheque": rs.cell_value(row, COL_N_CHEQUE),
            "total_ht": rs.cell_value(row, COL_HT),
            "total_tva": rs.cell_value(row, COL_TVA),
            "total_ttc": rs.cell_value(row, COL_TTC),
            "categorie": categorie,
        })
    return rows


def insert_invoice_into_workbook(template_bytes, data):
    """
    Insère une facture dans le template .xls en mémoire, en conservant
    la mise en forme d'origine. Les factures du même bloc sont triées
    par date (les dates non reconnues sont placées à la fin).
    Retourne (nouveaux_bytes, message_statut).
    """
    sheet_name = get_target_sheet_name(data["date"])
    if sheet_name is None:
        return template_bytes, f"❌ Impossible de déterminer le mois pour la date '{data['date']}' (ou onglet inexistant dans ce template)."

    payment_type = data.get("type_paiement", "").strip().upper()
    block_key = PAYMENT_TYPE_TO_BLOCK.get(payment_type)
    if block_key is None:
        return template_bytes, f"❌ Mode de paiement non reconnu : '{data.get('type_paiement')}'."

    rb = xlrd.open_workbook(file_contents=template_bytes, formatting_info=True)
    if sheet_name not in rb.sheet_names():
        return template_bytes, f"❌ L'onglet '{sheet_name}' n'existe pas dans ce fichier."

    sheet_idx = rb.sheet_names().index(sheet_name)
    rs = rb.sheet_by_index(sheet_idx)

    _, start_row, end_row = PAYMENT_BLOCKS[block_key]
    block_size = end_row - start_row + 1

    existing_rows = read_block_rows(rs, start_row, end_row)
    if len(existing_rows) >= block_size:
        return template_bytes, f"❌ Le bloc '{block_key}' de l'onglet '{sheet_name}' est déjà plein."

    new_row = {
        "fournisseur": data.get("fournisseur", ""),
        "date": data.get("date", ""),
        "type_paiement": payment_type,
        "n_cheque": data.get("n_cheque", ""),
        "total_ht": float(data.get("total_ht", 0) or 0),
        "total_tva": float(data.get("total_tva", 0) or 0),
        "total_ttc": float(data.get("total_ttc", 0) or 0),
        "categorie": data.get("categorie", "Divers"),
    }

    all_rows = existing_rows + [new_row]
    # Tri par date croissante ; les dates non reconnues passent à la fin, dans leur ordre d'arrivée.
    all_rows_indexed = list(enumerate(all_rows))
    all_rows_indexed.sort(
        key=lambda item: (parse_date(item[1]["date"]) is None, parse_date(item[1]["date"]) or datetime.max, item[0])
    )
    sorted_rows = [row for _, row in all_rows_indexed]
    new_row_position = next(i for i, (orig_i, _) in enumerate(all_rows_indexed) if orig_i == len(all_rows) - 1)

    wb = xl_copy(rb)
    ws = wb.get_sheet(sheet_idx)

    for i, row_data in enumerate(sorted_rows):
        target_row = start_row + i
        ws.write(target_row, COL_FOURNISSEUR, row_data["fournisseur"])
        ws.write(target_row, COL_DATE, row_data["date"])
        ws.write(target_row, COL_TYPE_PAIEMENT, row_data["type_paiement"])
        ws.write(target_row, COL_N_CHEQUE, row_data["n_cheque"])
        ws.write(target_row, COL_HT, float(row_data["total_ht"] or 0))
        ws.write(target_row, COL_TVA, float(row_data["total_tva"] or 0))
        ws.write(target_row, COL_TTC, float(row_data["total_ttc"] or 0))
        # OUI uniquement dans la bonne colonne de catégorie, rien dans les deux autres.
        for cat_name, col in COL_CATEGORIE.items():
            ws.write(target_row, col, "OUI" if cat_name == row_data["categorie"] else "")

    out = io.BytesIO()
    wb.save(out)
    final_row = start_row + new_row_position
    categorie = new_row["categorie"]
    msg = (
        f"✅ Ajoutée dans l'onglet **{sheet_name}**, bloc **{block_key}**, "
        f"ligne {final_row + 1} (triée par date), catégorie **{categorie}**."
    )
    return out.getvalue(), msg


# ============================================================
# INTERFACE
# ============================================================
st.title("🏨 Hotel Invoice Extractor")
st.divider()

if "master_bytes" not in st.session_state:
    st.session_state.master_bytes = None
    st.session_state.master_name = None
if "log" not in st.session_state:
    st.session_state.log = []
if "bank_log" not in st.session_state:
    st.session_state.bank_log = []

with st.sidebar:
    st.subheader("📁 Ton fichier de facturation")
    template_file = st.file_uploader("Uploade ton .xls (une seule fois)", type=["xls"])
    # On ne (re)charge le template QUE s'il s'agit d'un nouveau fichier,
    # sinon chaque rerun de l'app (ex: clic sur un bouton) écraserait
    # la progression déjà faite avec la version vierge.
    if template_file is not None and template_file.name != st.session_state.get("uploaded_template_name"):
        st.session_state.master_bytes = template_file.read()
        st.session_state.master_name = template_file.name
        st.session_state.uploaded_template_name = template_file.name
        st.session_state.log = []
        st.session_state.bank_log = []
        st.success(f"Chargé : {template_file.name}")
    elif st.session_state.master_bytes:
        st.caption(f"Fichier en cours : {st.session_state.master_name}")

    if st.session_state.master_bytes:
        st.divider()
        st.download_button(
            "📥 Télécharger le fichier à jour",
            data=st.session_state.master_bytes,
            file_name=st.session_state.master_name or "facturation_mise_a_jour.xls",
            mime="application/vnd.ms-excel",
            use_container_width=True,
        )

tab_factures, tab_releve = st.tabs(["📄 Factures", "🏦 Relevé bancaire"])

# ------------------------------------------------------------
# ONGLET 1 : FACTURES
# ------------------------------------------------------------
with tab_factures:
    st.markdown("**Upload tes factures — l'IA remplit le tableau automatiquement.**")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📄 Upload Invoice(s)")
        uploaded_files = st.file_uploader(
            "Choisis une ou plusieurs factures PDF", type="pdf", accept_multiple_files=True, key="invoice_uploader"
        )

    with col2:
        st.subheader("🤖 Extraction & remplissage")

        if not st.session_state.master_bytes:
            st.info("⬅️ Uploade d'abord ton template Excel dans la barre latérale.")
        elif not uploaded_files:
            st.info("Uploade une facture pour commencer.")
        else:
            if st.button("Extraire et remplir", type="primary", use_container_width=True, key="btn_factures"):
                for f in uploaded_files:
                    with st.spinner(f"Lecture de {f.name}..."):
                        try:
                            pdf_bytes = f.read()
                            image_bytes = extract_image_from_pdf(pdf_bytes)
                            data = extract_invoice_data(image_bytes, API_KEY)
                            new_bytes, msg = insert_invoice_into_workbook(
                                st.session_state.master_bytes, data
                            )
                            st.session_state.master_bytes = new_bytes
                            st.session_state.log.append({"fichier": f.name, "data": data, "statut": msg})
                        except Exception as e:
                            st.session_state.log.append(
                                {"fichier": f.name, "data": None, "statut": f"❌ Erreur : {e}"}
                            )

            if st.session_state.log:
                st.divider()
                for entry in reversed(st.session_state.log):
                    st.markdown(f"**{entry['fichier']}**")
                    st.write(entry["statut"])
                    if entry["data"]:
                        d = entry["data"]
                        st.caption(
                            f"{d.get('fournisseur','?')} — {d.get('date','?')} — "
                            f"{d.get('total_ttc','?')}€ TTC — {d.get('categorie','?')}"
                        )
                    st.divider()

                st.download_button(
                    "📥 Télécharger le fichier mis à jour",
                    data=st.session_state.master_bytes,
                    file_name=st.session_state.master_name or "facturation_mise_a_jour.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    key="download_factures",
                )

# ------------------------------------------------------------
# ONGLET 2 : RELEVÉ BANCAIRE
# ------------------------------------------------------------
with tab_releve:
    st.markdown(
        "**Upload un relevé de compte — l'IA extrait les lignes DEBIT de type "
        "CB / VIREMENT / PRELEVEMENT (hors commissions) et les ajoute au tableau.**"
    )
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🏦 Upload relevé bancaire")
        bank_file = st.file_uploader(
            "Choisis un relevé de compte PDF", type="pdf", key="bank_uploader"
        )

    with col2:
        st.subheader("🤖 Extraction & remplissage")

        if not st.session_state.master_bytes:
            st.info("⬅️ Uploade d'abord ton template Excel dans la barre latérale.")
        elif not bank_file:
            st.info("Uploade un relevé bancaire pour commencer.")
        else:
            if st.button("Extraire et remplir", type="primary", use_container_width=True, key="btn_releve"):
                pdf_bytes = bank_file.read()
                with st.spinner("Découpage du relevé en pages..."):
                    page_images = extract_pdf_page_images(pdf_bytes)

                all_transactions = []
                progress = st.progress(0.0)
                for i, img in enumerate(page_images):
                    with st.spinner(f"Analyse de la page {i + 1}/{len(page_images)}..."):
                        try:
                            transactions = extract_bank_transactions_from_page(img, API_KEY)
                            all_transactions.extend(transactions or [])
                        except Exception as e:
                            st.session_state.bank_log.append(
                                {"fichier": f"{bank_file.name} (page {i + 1})", "data": None, "statut": f"❌ Erreur : {e}"}
                            )
                    progress.progress((i + 1) / len(page_images))

                for t in all_transactions:
                    data = {
                        "fournisseur": t.get("description", ""),
                        "date": t.get("date", ""),
                        "type_paiement": t.get("type", ""),
                        "n_cheque": "",
                        "total_ht": 0.0,
                        "total_tva": 0.0,
                        "total_ttc": t.get("montant", 0.0),
                        "categorie": t.get("categorie", "Divers"),
                    }
                    try:
                        new_bytes, msg = insert_invoice_into_workbook(st.session_state.master_bytes, data)
                        st.session_state.master_bytes = new_bytes
                        st.session_state.bank_log.append({"fichier": bank_file.name, "data": data, "statut": msg})
                    except Exception as e:
                        st.session_state.bank_log.append(
                            {"fichier": bank_file.name, "data": data, "statut": f"❌ Erreur : {e}"}
                        )

                st.success(f"Terminé : {len(all_transactions)} transaction(s) trouvée(s) sur {len(page_images)} page(s).")

            if st.session_state.bank_log:
                st.divider()
                for entry in reversed(st.session_state.bank_log):
                    st.write(entry["statut"])
                    if entry["data"]:
                        d = entry["data"]
                        st.caption(
                            f"{d.get('fournisseur','?')} — {d.get('date','?')} — "
                            f"{d.get('total_ttc','?')}€ — {d.get('type_paiement','?')} — {d.get('categorie','?')}"
                        )
                    st.divider()

                st.download_button(
                    "📥 Télécharger le fichier mis à jour",
                    data=st.session_state.master_bytes,
                    file_name=st.session_state.master_name or "facturation_mise_a_jour.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    key="download_releve",
                )