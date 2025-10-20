from flask import Flask, request, render_template_string
from flask_mail import Mail, Message
import re

app = Flask(__name__)

# 📨 Config minimale pour que Flask-Mail fonctionne (SMTP fictif si tu veux juste tester Message)
app.config.update(
    MAIL_SERVER='localhost',
    MAIL_PORT=25,
    MAIL_DEFAULT_SENDER='no-reply@mobibenz.com'
)

mail = Mail(app)

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    email = ''
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        if email and EMAIL_REGEX.match(email):
            try:
                msg = Message(
                    subject="Test de création Message",
                    recipients=[email]
                )
                # pas besoin de mail.send pour ce test
                message = f"✅ Message créé avec succès pour : {email}"
            except Exception as e:
                message = f"❌ Erreur : {e}"
        else:
            message = f"📭 Email invalide ou vide : '{email}'"

    return render_template_string('''
    <form method="post">
        <input type="text" name="email" placeholder="Saisir un email de test" value="{{ email }}">
        <button type="submit">Tester</button>
    </form>
    {% if message %}
      <p>{{ message }}</p>
    {% endif %}
    ''', message=message, email=email)

if __name__ == '__main__':
    app.run(debug=True)
