from django.contrib import admin

from .models import (Artiste, Extrait, GenreMusical, Interview, Lieu, ProfilUtilisateur, Question,
                     QuestionExtrait)

# Les vidéos se gèrent surtout depuis la page « Administration » du site (/rec117/administration/).
# L'administration Django (/admin/) sert pour le reste : artistes, genres, lieux, questions, comptes.
for modele in (GenreMusical, Artiste, Lieu, Question, Interview, ProfilUtilisateur):
    admin.site.register(modele)


class QuestionExtraitInline(admin.TabularInline):
    """Questions d'un extrait (avec leur timecode), modifiables dans la page de l'extrait."""
    model = QuestionExtrait
    extra = 1


@admin.register(Extrait)
class ExtraitAdmin(admin.ModelAdmin):
    inlines = [QuestionExtraitInline]