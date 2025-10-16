import sqlite3

# 📌 Nom du fichier SQLite (dans ton projet Flask)
db_path = "demandes.db"

# 🧭 Connexion à la base
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1️⃣ Renommer l'ancienne table
c.execute("ALTER TABLE demandes RENAME TO demandes_old;")

# 2️⃣ Créer la nouvelle table sans la colonne 'description'
c.execute("""
CREATE TABLE demandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intervention_numero TEXT,
    entreprise TEXT,
    contact_nom TEXT,
    telephone TEXT,
    email TEXT,
    titre TEXT,
    type_support TEXT,
    detail_support TEXT,
    autre_detail TEXT,
    express INTEGER DEFAULT 0,
    date TEXT,
    statut TEXT
);
""")

# 3️⃣ Copier les données existantes dans la nouvelle table
c.execute("""
INSERT INTO demandes (
    id, intervention_numero, entreprise, contact_nom, telephone, email,
    titre, type_support, detail_support, autre_detail, express, date, statut
)
SELECT
    id, intervention_numero, entreprise, contact_nom, telephone, email,
    titre, type_support, detail_support, autre_detail, express, date, statut
FROM demandes_old;
""")

# 4️⃣ Supprimer l'ancienne table
c.execute("DROP TABLE demandes_old;")

# 5️⃣ Commit + fermeture
conn.commit()
conn.close()

print("✅ Colonne 'description' supprimée et données conservées.")
