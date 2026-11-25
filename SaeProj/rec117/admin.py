from django.contrib import admin

from .models import (
    Artiste,
    ConfigurationSite,
    Extrait,
    GenreMusical,
    Interview,
    Lieu,
    ProfilUtilisateur,
    Question,
)

# Les vidéos se gèrent surtout depuis la page « Administration » du site (/rec117/administration/).
# L'administration Django (/admin/) sert pour le reste : artistes, genres, lieux, questions, comptes.
for modele in (GenreMusical, Artiste, Lieu, Question, ProfilUtilisateur, ConfigurationSite):
    admin.site.register(modele)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("titreInterview", "artiste", "dateTournage", "dateMiseEnLigne")
    list_filter = ("artiste", "dateTournage", "dateMiseEnLigne")


@admin.register(Extrait)
class ExtraitAdmin(admin.ModelAdmin):
    list_display = ("titreExtrait", "interview", "ordreSequence", "dateMiseEnLigne")
    list_filter = ("interview__artiste", "dateMiseEnLigne")