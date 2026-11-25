"""Formulaires de la page d'administration des vidéos."""
import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Max

from .models import (Artiste, ConfigurationSite, Extrait, GenreMusical, Interview, Lieu,
                     ProfilUtilisateur, Question, QuestionExtrait)


class InscriptionForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = (
            'Votre mot de passe doit contenir au moins 8 caractères, ne pas être trop courant, '
            'ne pas être entièrement numérique et ne pas être trop proche de vos informations personnelles.'
        )
        self.fields['password2'].help_text = 'Saisissez à nouveau le même mot de passe pour le confirmer.'

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        utilisateur.is_staff = False
        utilisateur.is_superuser = False
        if commit:
            utilisateur.save()
        return utilisateur

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)


class ProfilUtilisateurForm(forms.ModelForm):
    class Meta:
        model = ProfilUtilisateur
        fields = ('lecteurPrefere',)
        labels = {'lecteurPrefere': 'Lecteur vidéo préféré'}


# --- Champ « durée » : accepte 253, 4:13 ou 1:04:13 ---------------------------

def formater_duree(secondes):
    """253 -> '4:13' ; 3853 -> '1:04:13'"""
    if secondes in (None, ''):
        return ''
    secondes = int(secondes)
    h, reste = divmod(secondes, 3600)
    m, s = divmod(reste, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


class DureeField(forms.CharField):
    """Saisie d'une durée ou d'un timecode, stockée en secondes."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'En secondes (253) ou en minutes:secondes (4:13 ou 1:04:13)')
        kwargs.setdefault('widget', forms.TextInput(attrs={'placeholder': 'ex : 4:13'}))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, int):
            return formater_duree(value)
        return value

    def to_python(self, value):
        value = (super().to_python(value) or '').strip()
        if not value:
            return None
        if not re.fullmatch(r'\d+(:\d{1,2}){0,2}', value):
            raise forms.ValidationError('Format attendu : 253, 4:13 ou 1:04:13')
        total = 0
        for morceau in value.split(':'):
            total = total * 60 + int(morceau)
        return total


class DateFrancaise(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


class ConfigurationSiteForm(forms.ModelForm):
    class Meta:
        model = ConfigurationSite
        fields = ['nombre_videos_carrousel']


# --- Interview -------------------------------------------------------------------

class InterviewForm(forms.ModelForm):
    # Regroupement des champs en blocs sur la page
    groupes = [
        ('🎬 La playlist', ['titreInterview', 'urlMiniature']),
        ('🎤 Artiste', ['artiste', 'nouvel_artiste', 'genres_nouvel_artiste', 'nouveau_genre', 'couleur_nouveau_genre']),
        ('📍 Tournage', ['dateTournage', 'dateMiseEnLigne', 'lieu', 'nouveau_lieu', 'ville_nouveau_lieu', 'pays_nouveau_lieu']),
        ('📝 Description', ['descriptionInterview']),
    ]
    # Créer un artiste ou un lieu directement depuis le formulaire
    nouvel_artiste = forms.CharField(
        label='… ou nouvel artiste', required=False, max_length=150,
        help_text="Remplir seulement si l'artiste n'est pas dans la liste")
    genres_nouvel_artiste = forms.ModelMultipleChoiceField(
        label='Genres du nouvel artiste', required=False, queryset=GenreMusical.objects.all(),
        widget=forms.CheckboxSelectMultiple)
    # Créer un genre musical directement depuis le formulaire (il est ajouté à l'artiste)
    nouveau_genre = forms.CharField(
        label='… ou nouveau genre', required=False, max_length=100,
        help_text="Remplir seulement si le genre n'est pas dans la liste. Il sera ajouté à l'artiste.")
    couleur_nouveau_genre = forms.CharField(
        label='Couleur du nouveau genre', required=False, initial='#00E5FF',
        widget=forms.TextInput(attrs={'type': 'color'}))
    nouveau_lieu = forms.CharField(label='… ou nouveau lieu (nom)', required=False, max_length=150)
    ville_nouveau_lieu = forms.CharField(label='Ville du nouveau lieu', required=False, max_length=100)
    pays_nouveau_lieu = forms.CharField(label='Pays du nouveau lieu', required=False, max_length=100, initial='France')

    class Meta:
        model = Interview
        fields = ['titreInterview', 'urlMiniature',
                  'artiste', 'nouvel_artiste', 'genres_nouvel_artiste', 'nouveau_genre', 'couleur_nouveau_genre',
                  'dateTournage', 'dateMiseEnLigne', 'lieu', 'nouveau_lieu', 'ville_nouveau_lieu', 'pays_nouveau_lieu',
                  'descriptionInterview']
        labels = {
            'titreInterview': 'Titre',
            'urlMiniature': 'Miniature (URL de l\'image)',
            'artiste': 'Artiste',
            'dateTournage': 'Date de tournage',
            'dateMiseEnLigne': 'Date de mise en ligne',
            'lieu': 'Lieu',
            'descriptionInterview': 'Description',
        }
        widgets = {
            'dateTournage': DateFrancaise(),
            'dateMiseEnLigne': DateFrancaise(),
            'descriptionInterview': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['artiste'].required = False
        self.fields['artiste'].empty_label = '— Choisir un artiste —'
        self.fields['lieu'].empty_label = '— Lieu non précisé —'

    def clean(self):
        donnees = super().clean()
        if not donnees.get('artiste') and not donnees.get('nouvel_artiste'):
            self.add_error('artiste', 'Choisissez un artiste dans la liste ou indiquez un nouvel artiste.')
        if donnees.get('nouveau_lieu') and not donnees.get('ville_nouveau_lieu'):
            self.add_error('ville_nouveau_lieu', 'Indiquez la ville du nouveau lieu.')
        couleur = donnees.get('couleur_nouveau_genre')
        if couleur and not re.fullmatch(r'#[0-9A-Fa-f]{6}', couleur):
            self.add_error('couleur_nouveau_genre', 'Format attendu : #RRGGBB, par exemple #1DB954.')
        return donnees

    def save(self, commit=True):
        interview = super().save(commit=False)
        donnees = self.cleaned_data
        if donnees.get('nouvel_artiste'):
            nom = donnees['nouvel_artiste'].strip()
            artiste = Artiste.objects.filter(nomArtiste__iexact=nom).first()
            if artiste is None:
                artiste = Artiste.objects.create(nomArtiste=nom)
            if donnees.get('genres_nouvel_artiste'):
                artiste.genres.add(*donnees['genres_nouvel_artiste'])
            interview.artiste = artiste
        if donnees.get('nouveau_genre'):
            nom = donnees['nouveau_genre'].strip()
            genre = GenreMusical.objects.filter(nomGenre__iexact=nom).first()
            if genre is None:
                genre = GenreMusical.objects.create(
                    nomGenre=nom, codeCouleur=donnees.get('couleur_nouveau_genre') or '#888888')
            interview.artiste.genres.add(genre)
        if donnees.get('nouveau_lieu'):
            interview.lieu, _ = Lieu.objects.get_or_create(
                nomLieu=donnees['nouveau_lieu'].strip(),
                villeLieu=donnees['ville_nouveau_lieu'].strip(),
                paysLieu=(donnees.get('pays_nouveau_lieu') or '').strip(),
            )
        if commit:
            interview.save()
        return interview


# --- Extrait ---------------------------------------------------------------------

class ExtraitForm(forms.ModelForm):
    groupes = [
        ('🎬 La vidéo', ['titreExtrait', 'urlYoutube', 'urlVimeo', 'urlMiniature', 'duree', 'dateMiseEnLigne']),
        ("🔗 Place dans l'interview", ['interview', 'ordreSequence']),
        ('📝 Transcription', ['transcription']),
    ]
    # Les questions et leurs timecodes ne sont plus ici : voir QuestionExtraitFormSet plus bas
    duree = DureeField(label='Durée', required=False)

    class Meta:
        model = Extrait
        fields = ['titreExtrait', 'urlYoutube', 'urlVimeo', 'urlMiniature', 'duree', 'dateMiseEnLigne',
                  'interview', 'ordreSequence', 'transcription']
        labels = {
            'titreExtrait': 'Titre',
            'urlYoutube': 'URL YouTube',
            'urlVimeo': 'URL Vimeo',
            'urlMiniature': 'Miniature (URL de l\'image)',
            'dateMiseEnLigne': 'Date de mise en ligne',
            'interview': 'Interview (playlist)',
            'ordreSequence': 'N° dans l\'interview',
            'transcription': 'Transcription / description',
        }
        help_texts = {
            'ordreSequence': 'Laisser vide pour le mettre à la suite des autres extraits',
        }
        widgets = {
            'dateMiseEnLigne': DateFrancaise(),
            'transcription': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interview'].empty_label = '— Choisir une interview —'
        self.fields['ordreSequence'].required = False

    def clean(self):
        donnees = super().clean()
        if not donnees.get('urlYoutube') and not donnees.get('urlVimeo'):
            self.add_error('urlYoutube', 'Indiquez au moins une URL YouTube ou Vimeo.')
        interview = donnees.get('interview')
        if donnees.get('ordreSequence') is None and interview:
            autres = interview.extraits.exclude(pk=self.instance.pk)
            donnees['ordreSequence'] = (autres.aggregate(m=Max('ordreSequence'))['m'] or 0) + 1
        return donnees


# --- Questions d'un extrait, avec leur timecode -----------------------------------
# Un « formset » est une liste de petits formulaires identiques : une ligne par question.
# Chaque ligne = une question (existante ou nouvelle) + le moment où elle commence dans la vidéo.

class QuestionExtraitForm(forms.ModelForm):
    # Champ « question » déclaré à la main (pas celui du modèle) pour pouvoir le laisser vide
    # quand on écrit une nouvelle question à la place.
    question = forms.ModelChoiceField(
        label='Question', required=False, queryset=Question.objects.all(),
        empty_label='— Choisir une question —')
    nouvelle_question = forms.CharField(
        label='… ou nouvelle question', required=False, max_length=500,
        widget=forms.TextInput(attrs={'placeholder': 'Écrire une nouvelle question'}))
    timecode = DureeField(
        label='Timecode', required=False,
        help_text='Moment où la question commence (ex : 1:20). Vide = 0:00',
        widget=forms.TextInput(attrs={'placeholder': '0:00'}))

    field_order = ['question', 'nouvelle_question', 'timecode']

    class Meta:
        model = QuestionExtrait
        fields = ['timecode']  # la question est gérée à la main, voir save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:  # modification : on pré-sélectionne la question déjà enregistrée
            self.initial['question'] = self.instance.question_id

    def clean(self):
        donnees = super().clean()
        if donnees.get('DELETE'):
            return donnees
        if not donnees.get('question') and not (donnees.get('nouvelle_question') or '').strip():
            self.add_error('question', 'Choisissez une question ou écrivez-en une nouvelle.')
        if donnees.get('timecode') is None:
            donnees['timecode'] = 0
        return donnees

    def texte_question(self):
        """Texte de la question de la ligne, en minuscules (pour repérer les doublons)."""
        nouvelle = (self.cleaned_data.get('nouvelle_question') or '').strip()
        if nouvelle:
            return nouvelle.lower()
        question = self.cleaned_data.get('question')
        return question.texteQuestion.strip().lower() if question else ''

    def save(self, commit=True):
        lien = super().save(commit=False)
        texte = (self.cleaned_data.get('nouvelle_question') or '').strip()
        if texte:
            lien.question = Question.objects.filter(texteQuestion__iexact=texte).first() \
                or Question.objects.create(texteQuestion=texte)
        else:
            lien.question = self.cleaned_data['question']
        if commit:
            lien.save()
        return lien


class BaseQuestionExtraitFormSet(forms.BaseInlineFormSet):
    """Vérifications sur l'ensemble des lignes (une ligne seule ne peut pas les faire)."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        duree = self.instance.duree
        deja_vues = set()
        nombre = 0
        for form in self.forms:
            if not form.has_changed() and not form.instance.pk:
                continue  # ligne vide laissée telle quelle
            if form.cleaned_data.get('DELETE'):
                continue
            nombre += 1
            texte = form.texte_question()
            if texte in deja_vues:
                form.add_error('question', 'Cette question est déjà dans la liste.')
            deja_vues.add(texte)
            timecode = form.cleaned_data.get('timecode') or 0
            if duree and timecode > duree:
                form.add_error('timecode', f'Le timecode dépasse la durée de la vidéo ({formater_duree(duree)}).')
        if nombre == 0:
            raise forms.ValidationError('Ajoutez au moins une question à cet extrait.')


QuestionExtraitFormSet = forms.inlineformset_factory(
    Extrait, QuestionExtrait,
    form=QuestionExtraitForm,
    formset=BaseQuestionExtraitFormSet,
    fields=['timecode'],
    extra=1,
    can_delete=True,
)


# --- Étape 1 : l'URL ---------------------------------------------------------------

class UrlForm(forms.Form):
    url = forms.CharField(label='URL de la vidéo', widget=forms.TextInput(
        attrs={'placeholder': 'https://youtu.be/…  ou  https://vimeo.com/…', 'autofocus': True}))