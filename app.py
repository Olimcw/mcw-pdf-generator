import os
import io
import base64
import requests
from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__)

# -------------------------------------------------------
# TÉLÉCHARGEMENT DES TEMPLATES AU DÉMARRAGE DU SERVEUR
# On stocke les URLs des images PNG dans des variables
# d'environnement Railway (on les configurera après)
# -------------------------------------------------------

def get_template_image(url):
    """Télécharge une image depuis une URL et la retourne comme objet PIL Image."""
    response = requests.get(url)
    return Image.open(io.BytesIO(response.content)).copy()

def get_font(size=30):
    """Charge une police bold, avec fallback si non disponible."""
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    except:
        return ImageFont.load_default()

# -------------------------------------------------------
# ROUTE PRINCIPALE — Make.com appellera cette URL
# -------------------------------------------------------

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Reçoit les données du membre depuis Make.com,
    génère le PDF personnalisé et le retourne.
    
    Données attendues (JSON) :
    {
        "prenom": "Riad",
        "nom": "Khediri",
        "wifi_user": "irkhediri",
        "wifi_pass": "IATIVEN",
        "langue": "FR"   ← ou "EN"
    }
    """
    data = request.get_json()

    # Récupérer les données envoyées par Make.com
    prenom    = data.get('prenom', '')
    nom       = data.get('nom', '')
    wifi_user = data.get('wifi_user', '')
    wifi_pass = data.get('wifi_pass', '')
    langue    = data.get('langue', 'FR').upper()

    red  = (200, 30, 30)
    font = get_font(30)

    # -------------------------------------------------------
    # GÉNÉRATION SELON LA LANGUE
    # -------------------------------------------------------

    if langue == 'FR':
        # URLs des templates FR (variables d'environnement Railway)
        page1_url = os.environ.get('FR_PAGE1_URL')
        page2_url = os.environ.get('FR_PAGE2_URL')

        # Charger les deux pages du template FR
        img1 = get_template_image(page1_url)
        img2 = get_template_image(page2_url)
        draw = ImageDraw.Draw(img1)

        # Écrire les credentials en rouge aux coordonnées précises
        # (coordonnées trouvées et validées dans notre session de test)
        draw.text((310, 488), wifi_user, font=font, fill=red)  # WiFi username
        draw.text((340, 523), wifi_pass, font=font, fill=red)  # WiFi password
        draw.text((310, 988), wifi_user, font=font, fill=red)  # Impression username
        draw.text((340, 1023), wifi_pass, font=font, fill=red) # Impression password

        pages = [img1, img2]

    else:  # EN
        # URLs des templates EN (variables d'environnement Railway)
        page1_url = os.environ.get('EN_PAGE1_URL')
        page2_url = os.environ.get('EN_PAGE2_URL')

        # Charger les deux pages du template EN
        img1 = get_template_image(page1_url)
        img2 = get_template_image(page2_url)
        draw = ImageDraw.Draw(img2)  # Dans le template EN, on modifie la PAGE 2

        # Coordonnées spécifiques au template EN
        draw.text((310, 566), wifi_user, font=font, fill=red)  # WiFi username
        draw.text((310, 604), wifi_pass, font=font, fill=red)  # WiFi password
        draw.text((310, 1036), wifi_user, font=font, fill=red) # Impression username
        draw.text((310, 1074), wifi_pass, font=font, fill=red) # Impression password

        pages = [img1, img2]

    # -------------------------------------------------------
    # ASSEMBLAGE DU PDF FINAL
    # On combine les deux pages en un seul fichier PDF
    # et on le retourne directement dans la réponse HTTP
    # -------------------------------------------------------

    pdf_buffer = io.BytesIO()  # Buffer en mémoire — pas besoin d'écrire sur disque
    W, H = letter
    c = canvas.Canvas(pdf_buffer, pagesize=letter)

    for i, page_img in enumerate(pages):
        # Convertir chaque page PIL en buffer PNG temporaire
        img_buffer = io.BytesIO()
        page_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        # Dessiner la page dans le PDF
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(img_buffer), 0, 0, width=W, height=H)
        c.showPage()

    c.save()
    pdf_buffer.seek(0)

    # Retourner le PDF comme fichier téléchargeable
    filename = f"Accueil_MCW_{prenom}_{nom}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

# -------------------------------------------------------
# ROUTE DE SANTÉ — pour vérifier que le serveur tourne
# -------------------------------------------------------

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "MCW PDF Generator is running"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
