import re
from pathlib import Path

# 📌 Fichiers source et destination
INPUT_FILE = Path("liste_interventions.html")
OUTPUT_FILE = Path("liste_interventions.min.html")

def minify_html(content: str) -> str:
    # Supprime les commentaires HTML
    content = re.sub(r'<!--(.*?)-->', '', content, flags=re.DOTALL)
    # Supprime les espaces multiples
    content = re.sub(r'\s+', ' ', content)
    # Supprime les espaces autour des balises
    content = re.sub(r'>\s+<', '><', content)
    # Supprime les espaces au début et à la fin
    return content.strip()

def main():
    if not INPUT_FILE.exists():
        print(f"❌ Fichier introuvable : {INPUT_FILE}")
        return

    original_content = INPUT_FILE.read_text(encoding="utf-8")
    minified_content = minify_html(original_content)
    OUTPUT_FILE.write_text(minified_content, encoding="utf-8")
    print(f"✅ Minification terminée !")
    print(f"📄 Fichier généré : {OUTPUT_FILE}")
    print(f"💾 Taille originale : {len(original_content)} caractères")
    print(f"✨ Taille minifiée  : {len(minified_content)} caractères")

if __name__ == "__main__":
    main()
