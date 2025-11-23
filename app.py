from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
from functools import wraps
import config
import os
import re
from zoneinfo import ZoneInfo
from flask import jsonify

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
        type_support TEXT,
        detail_support TEXT,
        autre_detail TEXT,
        express INTEGER DEFAULT 0,
        date TEXT,
        statut TEXT,
        date_planif TEXT,
        planif_confirmation_date TEXT,
        paiement TEXT DEFAULT 'NP'  -- 🆕 colonne ajoutée ici
        
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
    date_planif = None
    planif_confirmation_date = None

    intervention_numero = generate_intervention_number()
    date = now_local().strftime("%Y-%m-%d %H:%M:%S")
    statut = "En attente"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO demandes (
            intervention_numero, entreprise, contact_nom, telephone, email,
            titre, type_support, detail_support, autre_detail,
            express, date, statut, date_planif, planif_confirmation_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (intervention_numero, entreprise, contact_nom, telephone, email,
          titre, type_support, detail_support, autre_detail,
          express, date, statut, date_planif, planif_confirmation_date))  # 🗑️ description retirée ici
    conn.commit()
    # 🆔 Récupération de l'ID inséré
    inserted_id = c.lastrowid
    conn.close()

    # 🌐 Génération du PDF via PDFShift
    # pdf_bytes = None
    # try:
    #     import requests
    #     fiche_url = url_for('print_intervention', id=inserted_id, _external=True)
    #     api_key = "sk_0fcf9fb73101a0a9669c55c21a93d6eba5731dec"  # 🛑 remplace par ta clé API PDFShift

    #     response = requests.post(
    #         "https://api.pdfshift.io/v3/convert",
    #         auth=(api_key, ""),
    #         json={"source": fiche_url}
    #     )

    #     if response.status_code == 200:
    #         pdf_bytes = response.content
    #         print("✅ PDF généré avec succès depuis /print")
    #     else:
    #         print("⚠️ Erreur génération PDF:", response.text)
    # except Exception as e:
    #     print("⚠️ Exception génération PDF:", e)

    # 📬 Envoi du courriel si email valide
    try:
      # 🆔 Construction du lien vers la fiche
      lien_impression = url_for('print_intervention', id=inserted_id, _external=True)
      # ============================
      # 1) EMAIL AU CLIENT
      # ============================
      if email and EMAIL_REGEX.match(email):
        msg_client = Message(
            subject=f"Réception de votre demande - {intervention_numero}",
            recipients=[email]
        )
        # 🖼️ Version HTML
        msg_client.html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color:#f9f9f9; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
      
      <!-- Logo Mobibenz -->
      <div style="text-align:center; margin-bottom:20px;">
        <img src="https://mobibenz.com/support/static/img/logo_180x180.png" alt="Mobibenz" style="max-width:100px;">
      </div>

      <!-- Titre -->
      <h2 style="color:#1c3faa; text-align:center;">Réception de votre demande</h2>
      
      <!-- Message principal -->
      <p>Bonjour <strong>{contact_nom}</strong>,</p>
      <p>Nous avons bien reçu votre demande.</p>

      <p style="line-height:1.6;">
        <strong>Numéro de demande :</strong> {intervention_numero}<br>
        <strong>Date de soumission :</strong> {date}
      </p>

      <p>Notre équipe vous contactera sous peu afin de finaliser les détails.</p>

      <p>
        Merci de votre confiance.
      </p>

      <!-- ✨ Nouveau paragraphe pour imprimer la fiche -->
      <p style="margin-top:20px; text-align:center;">
        📎 <strong>Besoin d'un justificatif ?</strong><br>
        <a href="{lien_impression}" target="_blank" 
           style="color:#1c3faa; text-decoration:none; font-weight:bold;">
          Cliquez ici pour consulter ou imprimer la fiche de votre demande
        </a>
      </p>

      <!-- Bloc frais -->
        <div style="background:#f2f2f2; padding:15px; border-left:4px solid #f0ad4e; margin-top:20px; border-radius:4px;">
            <p style="margin:0 0 8px 0;">⚠️ <strong>Veuillez noter :</strong></p>
            <ul style="margin:0; padding-left:20px;">
              <li>Des frais de déplacement de <strong>minimum 3000 DA</strong> peuvent s'ajouter au coût de la prestation.</li>
              <li>L'option <strong>Service Express (intervention sous 24 h)</strong> est disponible avec un supplément de <strong>5000 DA</strong>.</li>
            </ul>
        </div>

      <!-- Footer -->
      <p style="margin-top:25px; text-align:center; font-size:0.9rem; color:#666;">
        <strong>Mobibenz Support</strong><br>
        📞 Support technique : 0557 75 56 60<br>
        🌐 <a href="https://mobibenz.com/support" style="color:#1c3faa;">mobibenz.com/support</a>
      </p>
    </div>
  </body>
</html>
"""
        # 📎 Pièce jointe si PDF généré
        # if pdf_bytes:
        #     msg.attach(
        #         f"{intervention_numero}.pdf",
        #         "application/pdf",
        #         pdf_bytes
        #     )
        
        mail.send(msg_client)
        print("Email envoyé")
      else:
        print("Email ignore (vide ou invalide).")

      # ============================
      # 2) EMAIL INTERNE MOBIBENZ
      # ============================
      msg_admin = Message(
        subject=f"📥 Nouvelle demande — {intervention_numero}",
        recipients=["support@mobibenz.com"]   # ← Mets ton email interne ici
      )

      msg_admin.html = f"""
      <html>
        <body style="font-family: Arial; color:#333; padding:20px;">
          <h2>Nouvelle demande reçue</h2>

          <p><strong>Numéro :</strong> {intervention_numero}</p>
          <p><strong>Date :</strong> {date}</p>

          <h3>Client</h3>
          <p><strong>Entreprise :</strong> {entreprise}</p>
          <p><strong>Nom :</strong> {contact_nom}</p>
          <p><strong>Téléphone :</strong> {telephone}</p>
          <p><strong>Email :</strong> {email}</p>

          <h3>Détails</h3>
          <p><strong>Titre :</strong> {titre}</p>
          <p><strong>Type support :</strong> {type_support}</p>
          <p><strong>Détail :</strong> {detail_support}</p>
          <p><strong>Autre :</strong> {autre_detail}</p>
          <p><strong>Express :</strong> {"Oui" if express else "Non"}</p>

          <p style="margin-top:20px;">
            🔗 <a href="{url_for('admin', _external=True)}">Ouvrir panneau admin</a>
          </p>
        </body>
      </html>
      """
      with mail.connect() as conn:
        conn.send(msg_admin)
        print("Email interne envoyé")

    except Exception as e:
      print(f"Erreur lors de l'envoi de l'email:", e)

    return redirect(url_for('merci', intervention=intervention_numero, id=inserted_id, email=email))

# ✅ Page de remerciement
@app.route('/merci')
def merci():
    intervention = request.args.get('intervention')
    id_demande = request.args.get('id')
    email = request.args.get('email')
    return render_template('merci.html', intervention=intervention, id=id_demande, email=email)

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
                 titre, type_support, detail_support, autre_detail, express, date, statut, date_planif, planif_confirmation_date, paiement
                 FROM demandes ORDER BY date DESC""")  # 🗑️ description retirée ici
    rows = c.fetchall()
    conn.close()
    return render_template('admin.html', demandes=rows)

# 📝 Maj statut
@app.route('/update_statut/<int:id>', methods=['POST'])
@login_required
def update_statut(id):
    data = request.get_json()           # 👈 lit le body JSON correctement
    new_statut = data.get('new_statut')
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
    c.execute("DELETE FROM demandes WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return ('', 204)  # ✅ Pas de redirection, réponse vide et succès

# 🖨️ Page imprimable
@app.route('/print/<int:id>')
def print_intervention(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""SELECT id, intervention_numero, entreprise, contact_nom, telephone, email,
                 titre, type_support, detail_support, autre_detail, express, date, statut, paiement
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


@app.route('/resend_confirmation/<int:id>', methods=['POST'])
def resend_confirmation(id):
    try:
        # 📌 Récupération des infos de la demande
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT intervention_numero, entreprise, contact_nom, telephone, email,
                   titre, type_support, detail_support, autre_detail, express, date
            FROM demandes
            WHERE id = ?
        """, (id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return "Demande introuvable", 404

        (intervention_numero, entreprise, contact_nom, telephone, email,
         titre, type_support, detail_support, autre_detail, express, date) = row

        # 🧾 Génération du lien d’impression (comme dans /submit)
        lien_impression = url_for('print_intervention', id=id, _external=True)

        # 📬 Envoi de l’e-mail si email valide
        if email and EMAIL_REGEX.match(email):
            msg = Message(
                subject=f"Réception de votre demande - {intervention_numero}",
                recipients=[email]
            )
            msg.html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color:#f9f9f9; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1);">
      
      <!-- Logo Mobibenz -->
      <div style="text-align:center; margin-bottom:20px;">
        <img src="https://mobibenz.com/support/static/img/logo_180x180.png" alt="Mobibenz" style="max-width:100px;">
      </div>

      <!-- Titre -->
      <h2 style="color:#1c3faa; text-align:center;">Réception de votre demande</h2>
      
      <!-- Message principal -->
      <p>Bonjour <strong>{contact_nom}</strong>,</p>
      <p>Nous vous confirmons une nouvelle fois la réception de votre demande.</p>

      <p style="line-height:1.6;">
        <strong>Numéro de demande :</strong> {intervention_numero}<br>
        <strong>Date de soumission :</strong> {date}
      </p>

      <p>Notre équipe vous contactera sous peu afin de finaliser les détails.</p>

      <p>
        Merci de votre confiance.
      </p>

      <!-- ✨ Lien fiche d'intervention -->
      <p style="margin-top:20px; text-align:center;">
        📎 <strong>Besoin d'un justificatif ?</strong><br>
        <a href="{lien_impression}" target="_blank" 
           style="color:#1c3faa; text-decoration:none; font-weight:bold;">
          Cliquez ici pour consulter ou imprimer la fiche de votre demande
        </a>
      </p>

      <!-- Bloc frais -->
      <div style="background:#f2f2f2; padding:15px; border-left:4px solid #f0ad4e; margin-top:20px; border-radius:4px;">
          <p style="margin:0 0 8px 0;">⚠️ <strong>Veuillez noter :</strong></p>
          <ul style="margin:0; padding-left:20px;">
            <li>Des frais de déplacement de <strong>minimum 3000 DA</strong> peuvent s'ajouter au coût de la prestation.</li>
            <li>L'option <strong>Service Express (intervention sous 24 h)</strong> est disponible avec un supplément de <strong>5000 DA</strong>.</li>
          </ul>
      </div>

      <!-- Footer -->
      <p style="margin-top:25px; text-align:center; font-size:0.9rem; color:#666;">
        <strong>Mobibenz Support</strong><br>
        📞 Support technique : 0557 75 56 60<br>
        🌐 <a href="https://mobibenz.com/support" style="color:#1c3faa;">mobibenz.com/support</a>
      </p>
    </div>
  </body>
</html>
"""
            mail.send(msg)
            print(f"Email de confirmation renvoye pour la demande {id}")
            return jsonify({"status": "ok"}), 200
        else:
            print(f"Aucun e-mail valide pour la demande {id}")
            return "Email invalide", 400

    except Exception as e:
        print(f"Erreur envoi confirmation : {e}")
        return str(e), 500


@app.route('/update_planif/<int:id>', methods=['POST'])
def update_planif(id):
    data = request.get_json()
    new_date = data.get('date_planif')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE demandes SET date_planif = ? WHERE id = ?", (new_date, id))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route('/send_planif_confirmation/<int:id>', methods=['POST'])
def send_planif_confirmation(id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT intervention_numero, entreprise, contact_nom, telephone, email, date_planif
            FROM demandes WHERE id = ?
        """, (id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return "Demande introuvable", 404

        intervention_numero, entreprise, contact_nom, telephone, email, date_planif = row

        if not email or not EMAIL_REGEX.match(email):
            return "Email invalide", 400

        if not date_planif:
            return "Aucune date planifiée pour cette intervention", 400

        # 🧾 Lien fiche intervention
        lien_impression = url_for('print_intervention', id=id, _external=True)

        # 📨 Construction de l'email
        msg = Message(
            subject=f"Confirmation de la date d'intervention - {intervention_numero}",
            recipients=[email]
        )
        msg.html = f"""
        <html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color:#f9f9f9; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1);">

      <!-- Logo Mobibenz -->
      <div style="text-align:center; margin-bottom:20px;">
        <img src="https://mobibenz.com/support/static/img/logo_180x180.png" alt="Mobibenz" style="max-width:100px;">
      </div>

      <!-- Titre -->
      <h2 style="color:#1c3faa; text-align:center;">Confirmation de la date d'intervention</h2>

      <!-- Message principal -->
      <p>Bonjour <strong>{contact_nom}</strong>,</p>

      <p>Votre demande a bien été planifiée par notre équipe technique.</p>

      <p style="line-height:1.6;">
        <strong>Numéro de demande :</strong> {intervention_numero}<br>
        <strong>Date et heure planifiées :</strong> {date_planif}
      </p>

      <p>
        Un technicien interviendra à la date prévue afin d'effectuer l'intervention. 
        Dans le cas où vous souhaiteriez modifier ou reporter cette date, nous vous prions de bien vouloir nous en informer <strong>au minimum 24 heures à l'avance</strong>.
      </p>

      <p>
        Merci de votre confiance.
      </p>

      <p style="margin-top:20px; text-align:center;">
        📎 <strong>Besoin d'un justificatif ?</strong><br>
        <a href="{lien_impression}" target="_blank" style="color:#1c3faa; text-decoration:none; font-weight:bold;">
          Cliquez ici pour consulter ou imprimer votre fiche d'intervention
        </a>
      </p>

      <div style="background:#f2f2f2; padding:15px; border-left:4px solid #1c3faa; margin-top:20px; border-radius:4px;">
        <p style="margin:0 0 8px 0;"><strong>Important :</strong></p>
        <ul style="margin:0; padding-left:20px;">
          <li>Merci de vous assurer que le lieu d'intervention est accessible à la date prévue.</li>
        </ul>
      </div>

      <!-- Footer -->
      <p style="margin-top:25px; text-align:center; font-size:0.9rem; color:#666;">
        <strong>Mobibenz Support</strong><br>
        📞 Support technique : 0557 75 56 60<br>
        🌐 <a href="https://mobibenz.com/support" style="color:#1c3faa;">mobibenz.com</a>
      </p>
    </div>
  </body>
</html>
        """
        mail.send(msg)
        timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        # 🕒 Enregistrer la date et l'heure d'envoi de la confirmation de planification
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE demandes SET planif_confirmation_date = ? WHERE id = ?",
            (datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"), id)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "timestamp": timestamp}), 200

    except Exception as e:
        print("❌ Erreur lors de l'envoi de l'e-mail planif:", e)
        return str(e), 500
    

@app.route('/resolve_and_notify/<int:id>', methods=['POST'])
def resolve_and_notify(id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # 🟢 1. Mettre à jour le statut en "Résolue"
        c.execute("UPDATE demandes SET statut = ? WHERE id = ?", ("Résolue", id))
        conn.commit()

        # 📩 2. Récupérer les infos du client
        c.execute("SELECT email, contact_nom, intervention_numero FROM demandes WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()

        if not row:
            return jsonify({"status": "error", "message": "Demande introuvable"}), 404

        email, contact_nom, intervention_numero = row

        # ✉️ 3. Envoyer le courriel si l’adresse est disponible
        if email and EMAIL_REGEX.match(email):
            msg = Message(
                subject=f"Demande {intervention_numero} — Résolue",
                recipients=[email]
            )
            msg.html = f"""
            <html>
  <body style="font-family: Arial, sans-serif; color: #333; background-color:#f9f9f9; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#ffffff; padding:20px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.1);">

      <!-- Logo Mobibenz -->
      <div style="text-align:center; margin-bottom:20px;">
        <img src="https://mobibenz.com/support/static/img/logo_180x180.png" alt="Mobibenz" style="max-width:100px;">
      </div>

      <!-- Titre -->
      <h2 style="color:#1c3faa; text-align:center;">Demande {intervention_numero} – Résolue</h2>

      <!-- Message principal -->
      <p>Bonjour <strong>{contact_nom}</strong>,</p>

      <p>
        Nous vous informons que votre demande <strong>{intervention_numero}</strong> a été 
        <strong>résolue</strong> et <strong>clôturée</strong> par notre équipe.
      </p>

      <p>
        Si vous avez besoin d'une assistance supplémentaire, nous vous invitons à soumettre une <strong>nouvelle demande</strong> via notre plateforme :
        <a href="https://mobibenz.com/support" style="color:#1c3faa; text-decoration:none;">mobibenz.com/support</a>.
      </p>

      <p>
        Merci de votre confiance.
      </p>

      <!-- Footer -->
      <p style="margin-top:25px; text-align:center; font-size:0.9rem; color:#666;">
        <strong>Mobibenz Support</strong><br>
        📞 Support technique : 0557 75 56 60<br>
        🌐 <a href="https://mobibenz.com/support" style="color:#1c3faa;">mobibenz.com/support</a>
      </p>
    </div>
  </body>
</html>
            """
            mail.send(msg)

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ Erreur resolve_and_notify:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/update_paiement/<int:id>', methods=['POST'])
@login_required
def update_paiement(id):
    data = request.get_json()
    new_paiement = data.get('new_paiement')  # 'NP', 'F' ou 'P'
    if new_paiement not in ('NP', 'F', 'P'):
        return jsonify({"status": "error", "message": "Valeur paiement invalide"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE demandes SET paiement = ? WHERE id = ?", (new_paiement, id))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# ✅ Appel immédiat au démarrage, que ce soit avec Flask, Gunicorn ou autre
init_db()

if __name__ == '__main__':
    app.run(debug=True)
