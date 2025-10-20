import smtplib
server = smtplib.SMTP("mail.mobibenz.com", 587)
server.starttls()
server.login("support@mobibenz.com", "Mohaja04")
print("✅ Connexion SMTP OK")
server.quit()
