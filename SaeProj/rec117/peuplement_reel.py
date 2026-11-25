import datetime
import html
import json
import re
import time
import urllib.parse
import urllib.request
from django.contrib.auth.models import User

# Remplace 'app' par le nom de ton application Django (ex: 'videos')
from .models import (
    GenreMusical,
    Artiste,
    Lieu,
    Question,
    Interview,
    Extrait,
    QuestionExtrait,
    ProfilUtilisateur,
)

# ==============================================================================
# SURCHARGE MANUELLE OPTIONNELLE (si une description n'indique pas la question)
# Clé : (nom_artiste, ordre) -> Valeur : "Intitulé exact de la question"
# ==============================================================================
QUESTIONS_SURCHARGE = {
    # ("Rivkah", 2): "Quel drôle de festival ?",
    # ("Rivkah", 4): "Quelle est ta prochaine étape ?",
}


def extraire_youtube_id(url: str) -> str:
    """Extrait l'identifiant vidéo (11 caractères) depuis une URL youtu.be ou youtube.com."""
    match = re.search(r"(?:youtu\.be/|v=|/embed/|/shorts/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else ""


def fetch_oembed_youtube(url: str) -> dict:
    """Interroge l'endpoint oEmbed officiel de YouTube avec l'URL canonique watch?v=ID."""
    video_id = extraire_youtube_id(url)
    canonical_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else url
    encoded_url = urllib.parse.quote(canonical_url, safe="")
    endpoint = f"https://www.youtube.com/oembed?url={encoded_url}&format=json"

    req = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"  [!] oEmbed YouTube échoué pour {canonical_url} : {e}")
        return {}


def fetch_oembed_vimeo(url: str) -> dict:
    """Interroge l'endpoint oEmbed officiel de Vimeo."""
    encoded_url = urllib.parse.quote(url, safe="")
    endpoint = f"https://vimeo.com/api/oembed.json?url={encoded_url}"

    req = urllib.request.Request(
        endpoint,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"  [!] oEmbed Vimeo échoué pour {url} : {e}")
        return {}


def fetch_youtube_description(url: str) -> str:
    """Récupère la description complète depuis la page YouTube."""
    video_id = extraire_youtube_id(url)
    watch_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else url

    req = urllib.request.Request(
        watch_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Cookie": "SOCS=CAESEwgDEgk0ODE3Nzk3MjQaAmZyIAEaBgiA_LyaBg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            page_html = response.read().decode("utf-8", errors="ignore")

        desc_match = re.search(r'"shortDescription"\s*:\s*"((?:[^"\\]|\\.)*)"', page_html)
        if desc_match:
            return json.loads(f'"{desc_match.group(1)}"').strip()

        og_desc = re.search(r'<meta property="og:description" content="([^"]*)"', page_html)
        if og_desc:
            return html.unescape(og_desc.group(1)).strip()
    except Exception:
        pass
    return ""


def nettoyer_libelle_question(texte: str, nom_artiste: str) -> str:
    """Nettoie un libellé de question et ajoute '?' si nécessaire."""
    texte = re.sub(rf"(?i)^{re.escape(nom_artiste)}\s*[\-:|/–—]\s*", "", texte).strip()
    texte = re.sub(
        r"(?i)^[\s\-:|/–—#]*(?:(?:interview|extrait|question|part|partie)\s*\d+|q\s*\d+|\d+)\s*[\-:|/–—.)]+\s*",
        "",
        texte,
    ).strip(" -:|/–—•*")

    if not texte:
        return ""

    texte = texte[0].upper() + texte[1:]

    mots_interrogatifs = (
        "comment", "pourquoi", "quel", "quelle", "quels", "quelles",
        "qui", "que", "quoi", "où", "quand", "combien", "est-ce"
    )
    if not texte.endswith(("?", "!", ".")) and any(
        re.search(rf"(?i)\b{mot}\b", texte) for mot in mots_interrogatifs
    ):
        texte += " ?"

    return texte


def extraire_question_extrait(titre: str, description: str, nom_artiste: str, ordre: int) -> str:
    """
    Extrait la vraie question de l'extrait :
    1. Vérifie QUESTIONS_SURCHARGE si défini manuellement.
    2. Cherche une phrase interrogative ('?') dans la description YouTube ou Vimeo.
    3. Cherche une ligne spécifique dans la description (hors phrase générique d'intro).
    4. Fallback sur le titre de la vidéo nettoyé.
    """
    if (nom_artiste, ordre) in QUESTIONS_SURCHARGE:
        return QUESTIONS_SURCHARGE[(nom_artiste, ordre)]

    lignes = [l.strip(" -•*\t") for l in description.splitlines() if l.strip()]

    # 1. Priorité absolue : une ligne contenant un '?' dans la description
    for ligne in lignes:
        if "?" in ligne and 8 <= len(ligne) <= 200:
            return nettoyer_libelle_question(ligne, nom_artiste)

    # 2. Deuxième priorité : une ligne de la description qui n'est pas l'intro générique
    for ligne in lignes:
        if (
            not ligne.lower().startswith("interview de sortie de scène")
            and not ligne.lower().startswith("http")
            and 8 <= len(ligne) <= 180
        ):
            return nettoyer_libelle_question(ligne, nom_artiste)

    # 3. Fallback sur le titre de la vidéo
    question_titre = nettoyer_libelle_question(titre, nom_artiste)
    return question_titre if question_titre else f"{nom_artiste} - Question {ordre}"


def parser_date_vimeo(upload_date_str: str) -> datetime.date:
    if upload_date_str:
        try:
            return datetime.datetime.strptime(upload_date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return datetime.date(2025, 1, 15)


def recuperer_infos_artiste(liste_liens: list[dict], nom_artiste: str):
    """Récupère les métadonnées YouTube et Vimeo pour chaque extrait."""
    for item in liste_liens:
        meta_yt = fetch_oembed_youtube(item["youtube"])
        meta_vimeo = fetch_oembed_vimeo(item["vimeo"])
        description_yt = fetch_youtube_description(item["youtube"])
        time.sleep(0.3)

        titre_yt = (meta_yt.get("title") or "").strip()
        titre_vimeo = (meta_vimeo.get("title") or "").strip()
        description_vimeo = (meta_vimeo.get("description") or "").strip()

        titre_final = titre_yt or titre_vimeo or f"{nom_artiste} - Extrait {item['ordre']}"
        description_finale = description_yt or description_vimeo or ""

        print(f"  [Extrait {item['ordre']}]")
        print(f"    Titre YT    : {titre_yt}")
        print(f"    Titre Vimeo : {titre_vimeo}")
        print(f"    Description : {description_finale!r}")

        item["infos"] = {
            "titre": titre_final,
            "description": description_finale,
            "meta_vimeo": meta_vimeo,
            "meta_yt": meta_yt,
        }


def run():
    print("=== Population de la base via oEmbed (Rivkah & Gontard) ===")

    # 1. Nettoyage de la base
    Extrait.objects.all().delete()
    Interview.objects.all().delete()
    Question.objects.all().delete()
    Lieu.objects.all().delete()
    Artiste.objects.all().delete()
    GenreMusical.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()

    print("[1/6] Anciennes données supprimées.")

    # 2. Genres & Couleurs musicales
    pop_indie = GenreMusical.objects.create(nomGenre="Pop / Indie", codeCouleur="#EC4899")
    chanson_rock = GenreMusical.objects.create(nomGenre="Chanson / Rock", codeCouleur="#E50914")

    print("[2/6] Genres musicaux créés.")

    # 3. Artistes
    rivkah = Artiste.objects.create(nomArtiste="Rivkah")
    rivkah.genres.add(pop_indie)

    gontard = Artiste.objects.create(nomArtiste="Gontard")
    gontard.genres.add(chanson_rock)

    print("[3/6] Artistes Rivkah et Gontard créés.")

    # 4. Lieu de tournage
    lieu = Lieu.objects.create(
        nomLieu="Supersonic Records",
        villeLieu="Paris",
        paysLieu="France"
    )

    # 5. Liens vidéos
    liens_rivkah = [
        {"ordre": 1, "vimeo": "https://vimeo.com/1128762950", "youtube": "https://youtu.be/1NYQ65FTEC8"},
        {"ordre": 2, "vimeo": "https://vimeo.com/1128763050", "youtube": "https://youtu.be/ux6ZtL1o0R0"},
        {"ordre": 3, "vimeo": "https://vimeo.com/1128763155", "youtube": "https://youtu.be/WpFoiw2uP0w"},
        {"ordre": 4, "vimeo": "https://vimeo.com/1128763765", "youtube": "https://youtu.be/2PDvQ3P8c64"},
    ]

    liens_gontard = [
        {"ordre": 1, "vimeo": "https://vimeo.com/1128786403", "youtube": "https://youtu.be/9eLoUEBF6no"},
        {"ordre": 2, "vimeo": "https://vimeo.com/1128786928", "youtube": "https://youtu.be/Wt14RXtzZxI"},
        {"ordre": 3, "vimeo": "https://vimeo.com/1128788337", "youtube": "https://youtu.be/IqLw5KDf9Fg"},
        {"ordre": 4, "vimeo": "https://vimeo.com/1128790175", "youtube": "https://youtu.be/uwIyaln-k8A"},
    ]

    print("[4/6] Récupération des métadonnées (YouTube + Vimeo) :")
    print("--- Rivkah ---")
    recuperer_infos_artiste(liens_rivkah, "Rivkah")
    print("--- Gontard ---")
    recuperer_infos_artiste(liens_gontard, "Gontard")

    # 6. Interview Rivkah
    date_rivkah = parser_date_vimeo(liens_rivkah[0]["infos"]["meta_vimeo"].get("upload_date", ""))
    auteur_rivkah = (
        liens_rivkah[0]["infos"]["meta_yt"].get("author_name")
        or liens_rivkah[0]["infos"]["meta_vimeo"].get("author_name")
        or "la chaîne officielle"
    )
    interview_rivkah = Interview.objects.create(
        titreInterview="Interview Rivkah",
        dateTournage=date_rivkah,
        descriptionInterview=f"Interview de sortie de scène de Rivkah ({auteur_rivkah}) décortiquée en 4 extraits.",
        artiste=rivkah,
        lieu=lieu,
    )

    print("\n--- QUESTIONS RETENUES RIVKAH ---")
    for item in liens_rivkah:
        infos = item["infos"]
        texte_question = extraire_question_extrait(
            infos["titre"], infos["description"], "Rivkah", item["ordre"]
        )
        question_obj = Question.objects.create(texteQuestion=texte_question)

        extrait = Extrait.objects.create(
            titreExtrait=infos["titre"],
            ordreSequence=item["ordre"],
            urlVimeo=item["vimeo"],
            urlYoutube=item["youtube"],
            transcription=infos["description"] or f"Transcription de : {infos['titre']}.",
            interview=interview_rivkah,
        )
        # La question de la vidéo, au début (timecode 0) : à affiner ensuite dans l'administration
        QuestionExtrait.objects.create(extrait=extrait, question=question_obj, timecode=0)
        print(f"  [{item['ordre']}] {infos['titre']}  ==>  Question : {texte_question}")

    # 7. Interview Gontard
    date_gontard = parser_date_vimeo(liens_gontard[0]["infos"]["meta_vimeo"].get("upload_date", ""))
    auteur_gontard = (
        liens_gontard[0]["infos"]["meta_yt"].get("author_name")
        or liens_gontard[0]["infos"]["meta_vimeo"].get("author_name")
        or "la chaîne officielle"
    )
    interview_gontard = Interview.objects.create(
        titreInterview="Interview Gontard",
        dateTournage=date_gontard,
        descriptionInterview=f"Interview de sortie de scène de Gontard ({auteur_gontard}) décortiquée en 4 extraits.",
        artiste=gontard,
        lieu=lieu,
    )

    print("\n--- QUESTIONS RETENUES GONTARD ---")
    for item in liens_gontard:
        infos = item["infos"]
        texte_question = extraire_question_extrait(
            infos["titre"], infos["description"], "Gontard", item["ordre"]
        )
        question_obj = Question.objects.create(texteQuestion=texte_question)

        extrait = Extrait.objects.create(
            titreExtrait=infos["titre"],
            ordreSequence=item["ordre"],
            urlVimeo=item["vimeo"],
            urlYoutube=item["youtube"],
            transcription=infos["description"] or f"Transcription de : {infos['titre']}.",
            interview=interview_gontard,
        )
        # La question de la vidéo, au début (timecode 0) : à affiner ensuite dans l'administration
        QuestionExtrait.objects.create(extrait=extrait, question=question_obj, timecode=0)
        print(f"  [{item['ordre']}] {infos['titre']}  ==>  Question : {texte_question}")

    print("\n[5/6] 2 interviews et 8 extraits créés.")

    # 8. Les 2 profils de base
    profils = [
        ("admin", "rec117", True),
        ("test", "test", False),
    ]
    for identifiant, mot_de_passe, est_admin in profils:
        user, _ = User.objects.get_or_create(username=identifiant)
        user.set_password(mot_de_passe)
        user.is_staff = est_admin
        user.is_superuser = est_admin
        user.save()
        ProfilUtilisateur.objects.get_or_create(user=user, defaults={"lecteurPrefere": "YOUTUBE"})

    print("[6/6] Profils créés : admin / rec117 (administrateur) et test (utilisateur simple).")
    print("=== Base de données peuplée avec succès ! ===")


if __name__ == "__main__":
    run()