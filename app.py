from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
from functools import wraps
import config
import os
import re
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "demandes.db")
TZ = ZoneInfo("Africa/Algiers")
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

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
    entreprise = request.form.get('entreprise', '').strip()
    contact_nom = request.form.get('contact_nom', '').strip()
    telephone = request.form.get('telephone', '').strip()
    email = request.form.get('email', '').strip()
    titre = request.form.get('titre', '').strip()
    # 🗑️ description retirée ici

    type_support = request.form.get('type_support', '').strip()
    detail_support = request.form.get('detail_support', '').strip()
    autre_detail = request.form.get('autre_detail', '').strip()

    express = 1 if 'express' in request.form else 0

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
    # 🆔 Récupération de l'ID inséré
    inserted_id = c.lastrowid
    conn.close()

    # 📬 Envoi du courriel si email valide
    if email and EMAIL_REGEX.match(email):
        try:
            msg = Message(
                subject=f"Confirmation de votre demande de support {intervention_numero}",
                recipients=[email]
)
            # 🖼️ Version HTML
            msg.html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color:#f9f9f9; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
      
      <!-- Logo Mobibenz -->
      <div style="text-align:center; margin-bottom:20px;">
        <img src="https://mobibenz.com/support/static/img/logo.jpg" alt="Mobibenz" style="max-width:180px;">
      </div>

      <!-- Titre -->
      <h2 style="color:#1c3faa; text-align:center;">Confirmation de votre demande de support</h2>
      
      <!-- Message principal -->
      <p>Bonjour <strong>{contact_nom}</strong>,</p>
      <p>Nous avons bien reçu votre demande de support.</p>

      <p style="line-height:1.6;">
        <strong>Numéro de demande :</strong> {intervention_numero}<br>
        <strong>Date de soumission :</strong> {date}
      </p>

      <p>Notre équipe vous contactera sous peu pour finaliser les détails de l'intervention.</p>

      <p>📎 Vous trouverez également la fiche d'intervention en pièce jointe à ce courriel.</p>

      <!-- Bloc frais -->
        <div style="background:#f2f2f2; padding:15px; border-left:4px solid #f0ad4e; margin-top:20px; border-radius:4px;">
            <p style="margin:0 0 8px 0;">⚠️ <strong>Veuillez noter :</strong></p>
            <ul style="margin:0; padding-left:20px;">
              <li>Des frais de déplacement de <strong>minimum 3000 DA</strong> peuvent s'ajouter au coût de la prestation.</li>
              <li>L'option <strong>Service Express (intervention sous 24 h)</strong> est disponible avec un supplément de <strong>5000 DA</strong>.</li>
            </ul>
        </div>

      <!-- Footer -->
      <p style="margin-top:25px; text-align:center;">
        Merci pour votre confiance,<br>
        <strong>Mobibenz Support</strong><br>
        <a href="https://mobibenz.com/support" style="color:#1c3faa; text-decoration:none;">mobibenz.com</a>
      </p>
    </div>
  </body>
</html>
"""
            #mail.send(msg)
            print(f"✅ Courriel envoyé à {email}")
        except Exception as e:
            print(f"⚠️ Erreur envoi mail ({email}):", e)
    else:
        print("📭 Email ignoré (vide ou invalide).")

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
