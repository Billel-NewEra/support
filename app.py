from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
from functools import wraps
import config
import os
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "demandes.db")
TZ = ZoneInfo("Africa/Algiers")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

@app.before_request
def set_script_name():
    request.environ['SCRIPT_NAME'] = '/support'

# 📬 Configuration Flask-Mail
app.config.update(
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_USE_TLS=config.MAIL_USE_TLS,
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=config.MAIL_DEFAULT_SENDER
)
mail = Mail(app)

def now_local():
    return datetime.now(TZ)

# 🗃️ Initialisation DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS demandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intervention_numero TEXT,
        entreprise TEXT,
        contact_nom TEXT,
        telephone TEXT,
        email TEXT,
        titre TEXT,
        -- 🗑️ description supprimée
        type_support TEXT,
        detail_support TEXT,
        autre_detail TEXT,
        express INTEGER DEFAULT 0,
        date TEXT,
        statut TEXT
    )
    """)
    conn.commit()
    conn.close()

# 🧮 Génération du numéro d'intervention
def generate_intervention_number():
    today_str = now_local().strftime("%Y%m%d")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM demandes WHERE date LIKE ?", (f"{now_local().strftime('%Y-%m-%d')}%",))
    count_today = c.fetchone()[0] + 1
    conn.close()
    return f"MBZ-{today_str}-{count_today:04d}"

# 🔐 Décorateur admin
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 🌐 Formulaire client
@app.route('/')
def support_form():
    return render_template('support.html')

# 📥 Soumission formulaire
@app.route('/submit', methods=['POST'])
def submit():
    entreprise = request.form['entreprise']
    contact_nom = request.form['contact_nom']
    telephone = request.form['telephone']
    email = request.form['email']
    titre = request.form['titre']
    # 🗑️ description retirée ici

    type_support = request.form['type_support']
    detail_support = request.form['detail_support']
    autre_detail = request.form.get('autre_detail', '')

    express = 1 if 'express' in request.form else 0

    # Si email est vide → on le remplace par None (pour insertion NULL en base)
    if not email:
        email = None

    intervention_numero = generate_intervention_number()
    date = now_local().strftime("%Y-%m-%d %H:%M:%S")
    statut = "En attente"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO demandes (
            intervention_numero, entreprise, contact_nom, telephone, email,
            titre, type_support, detail_support, autre_detail,
            express, date, statut
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (intervention_numero, entreprise, contact_nom, telephone, email,
          titre, type_support, detail_support, autre_detail,
          express, date, statut))  # 🗑️ description retirée ici
    conn.commit()
    conn.close()

    # ✉️ Mail client
    if email:
        msg = Message(f"Confirmation de votre intervention {intervention_numero}", recipients=[email])
        msg.body = f"""
Bonjour {contact_nom},

Nous avons bien reçu votre demande d'intervention.

Numéro d'intervention : {intervention_numero}

Notre équipe vous contactera sous peu pour finaliser les détails.
Merci pour votre confiance,
Support Mobibenz
"""
        try:
            mail.send(msg)
        except Exception as e:
            print("⚠️ Erreur envoi mail:", e)

    return redirect(url_for('merci', intervention=intervention_numero))

# ✅ Page de remerciement
@app.route('/merci')
def merci():
    intervention = request.args.get('intervention')
    return render_template('merci.html', intervention=intervention)

# 🔐 Login admin
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == config.ADMIN_USERNAME and request.form['password'] == config.ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# 📊 Interface admin
@app.route('/admin')
@login_required
def admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, intervention_numero, entreprise, contact_nom, telephone, email,
                 titre, type_support, detail_support, autre_detail, express, date, statut
                 FROM demandes ORDER BY date DESC""")  # 🗑️ description retirée ici
    rows = c.fetchall()
    conn.close()
    return render_template('admin.html', demandes=rows)

# 📝 Maj statut
@app.route('/update_statut/<int:id>', methods=['POST'])
@login_required
def update_statut(id):
    new_statut = request.form['new_statut']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE demandes SET statut = ? WHERE id = ?", (new_statut, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# 🗑️ Suppression
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_demande(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT statut FROM demandes WHERE id = ?", (id,))
    result = c.fetchone()

    if result and result[0] == "En attente":
        c.execute("DELETE FROM demandes WHERE id = ?", (id,))
        conn.commit()
        flash("✅ L'intervention a été supprimée avec succès.", "success")
    else:
        flash("❌ Suppression refusée — l'intervention n'est pas en attente.", "danger")

    conn.close()
    return redirect(url_for('admin'))

# 🖨️ Page imprimable
@app.route('/print/<int:id>')
def print_intervention(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, intervention_numero, entreprise, contact_nom, telephone, email,
                 titre, type_support, detail_support, autre_detail, express, date, statut
                 FROM demandes WHERE id = ?""", (id,))  # 🗑️ description retirée ici
    demande = c.fetchone()
    conn.close()
    year = now_local().year

    return render_template('print_intervention.html', d=demande, year=year)

# ✏️ Edition intervention
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_demande(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        telephone = request.form['telephone']
        email = request.form['email']
        titre = request.form['titre']
        # 🗑️ description retirée ici
        type_support = request.form['type_support']
        detail_support = request.form['detail_support']
        autre_detail = request.form.get('autre_detail', '')
        express = 1 if 'express' in request.form else 0

        c.execute("""
            UPDATE demandes
            SET telephone = ?, email = ?, titre = ?,
                type_support = ?, detail_support = ?, autre_detail = ?, express = ?
            WHERE id = ?
        """, (telephone, email, titre, type_support, detail_support, autre_detail, express, id))  # 🗑️ description retirée ici
        conn.commit()
        conn.close()
        flash("✅ Intervention mise à jour avec succès.", "success")
        return redirect(url_for('admin'))

    # GET — on récupère les infos actuelles
    c.execute("""
        SELECT id, intervention_numero, entreprise, contact_nom, telephone, email,
               titre, type_support, detail_support, autre_detail, express
        FROM demandes WHERE id = ?
    """, (id,))  # 🗑️ description retirée ici
    demande = c.fetchone()
    conn.close()

    return render_template('edit.html', d=demande)

# ✅ Appel immédiat au démarrage, que ce soit avec Flask, Gunicorn ou autre
init_db()

if __name__ == '__main__':
    app.run(debug=True)
