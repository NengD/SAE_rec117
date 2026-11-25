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
    QuestionExtrait,
)

# Les vidéos se gèrent surtout depuis la page « Administration » du site (/rec117/administration/).
# L'administration Django (/admin/) sert pour le reste : artistes, genres, lieux, questions, comptes.
for modele in (GenreMusical, Artiste, Lieu, Question, ProfilUtilisateur, ConfigurationSite):
    admin.site.register(modele)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("titreInterview", "artiste", "dateTournage", "dateMiseEnLigne")
    list_filter = ("artiste", "dateTournage", "dateMiseEnLigne")


class QuestionExtraitInline(admin.TabularInline):
    """Questions d'un extrait (avec leur timecode), modifiables dans la page de l'extrait."""
    model = QuestionExtrait
    extra = 1


@admin.register(Extrait)
class ExtraitAdmin(admin.ModelAdmin):
    inlines = [QuestionExtraitInline]
    list_display = ("titreExtrait", "interview", "ordreSequence", "dateMiseEnLigne")
    list_filter = ("interview__artiste", "dateMiseEnLigne")