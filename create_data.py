import pandas as pd

# Fake S&OP data similar to Safran
data = {
    "Poste de charge": [
        "Assemblage Structure", "Assemblage Structure", "Assemblage Structure",
        "Usinage CNC", "Usinage CNC", "Usinage CNC",
        "Contrôle Qualité", "Contrôle Qualité", "Contrôle Qualité",
        "Peinture", "Peinture", "Peinture"
    ],
    "Programme": [
        "A320", "A350", "B787",
        "A320", "A350", "B787",
        "A320", "A350", "B787",
        "A320", "A350", "B787"
    ],
    "Semaine": [
        "S28", "S28", "S28",
        "S28", "S28", "S28",
        "S28", "S28", "S28",
        "S28", "S28", "S28"
    ],
    "Capacité (heures)": [
        120, 120, 120,
        80, 80, 80,
        60, 60, 60,
        40, 40, 40
    ],
    "Charge (heures)": [
        95, 110, 85,
        75, 90, 60,
        55, 65, 45,
        35, 42, 30
    ],
    "Taux de charge (%)": [
        79, 92, 71,
        94, 113, 75,
        92, 108, 75,
        88, 105, 75
    ],
    "Statut": [
        "OK", "ATTENTION", "OK",
        "ATTENTION", "SURCHARGE", "OK",
        "ATTENTION", "SURCHARGE", "OK",
        "OK", "SURCHARGE", "OK"
    ]
}

df = pd.DataFrame(data)
df.to_excel("safran_sop_data.xlsx", index=False)
print("✅ Safran S&OP data created!")
print(df)