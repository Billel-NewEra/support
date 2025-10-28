import sqlite3

# ⚠️ adapte le chemin à ta base de prod
conn = sqlite3.connect('demandes.db')
cur = conn.cursor()

# ✅ Ajout de la colonne paiement avec valeur par défaut
cur.execute("ALTER TABLE demandes ADD COLUMN paiement TEXT DEFAULT 'NP';")

conn.commit()
conn.close()

print("✅ Colonne 'paiement' ajoutée avec succès.")