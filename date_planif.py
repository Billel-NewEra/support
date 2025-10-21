import sqlite3

DB_PATH = "demandes.db"  # adapte selon ton chemin

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ➕ Ajout de la colonne date_planif si elle n'existe pas
try:
    c.execute("ALTER TABLE demandes ADD COLUMN date_planif TEXT")
except sqlite3.OperationalError:
    print("Colonne date_planif existe déjà ✅")

# ➕ Ajout de la colonne planif_confirmation_date si elle n'existe pas
try:
    c.execute("ALTER TABLE demandes ADD COLUMN planif_confirmation_date TEXT")
except sqlite3.OperationalError:
    print("Colonne planif_confirmation_date existe déjà ✅")

conn.commit()
conn.close()
print("✅ Migration terminée.")
