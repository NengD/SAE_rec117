from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, UpdateView

from rec117.forms import InscriptionForm, ProfilUtilisateurForm
from rec117.models import (Artiste, ConfigurationSite, Extrait, GenreMusical, Interview,
                            Lieu, ProfilUtilisateur, Question)

NB_CONTENUS_RECENTS_PAR_DEFAUT = 10


class ConnexionUtilisateurView(LoginView):
    template_name = "rec117/administration/connexion_utilisateur.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        return reverse("home")


class HomeView(TemplateView):
    template_name = "rec117/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Données pour les filtres
        context['genres'] = GenreMusical.objects.all()
        context['lieux'] = Lieu.objects.all()
        context['artistes'] = Artiste.objects.all()

        # Données pour les carrousels et les fiches de la modale
        context['extraits'] = Extrait.objects.all()
        context['interviews'] = Interview.objects.order_by('idInterview')
        nombre_videos = ConfigurationSite.objects.values_list('nombre_videos_carrousel', flat=True).first()
        nombre_videos = nombre_videos or NB_CONTENUS_RECENTS_PAR_DEFAUT
        context['derniers_extraits'] = Extrait.objects.order_by('-idExtrait')[:nombre_videos]
        context['dernieres_interviews'] = Interview.objects.order_by('-idInterview')[:nombre_videos]

        # Interview à la une : la dernière ajoutée en base
        context['interview_a_la_une'] = Interview.objects.order_by('idInterview').last()

        return context


class MindMapView(TemplateView):
    template_name = "rec117/mindmap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Données pour les branches de la carte
        context['artistes'] = Artiste.objects.all()
        context['questions'] = Question.objects.all()
        context['genres'] = GenreMusical.objects.all()
        context['lieux'] = Lieu.objects.all()

        # Données pour les fiches de la modale
        context['interviews'] = Interview.objects.order_by('idInterview')
        context['extraits'] = Extrait.objects.all()

        return context


class ProfilUtilisateurView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):
    template_name = "rec117/profil.html"
    model = ProfilUtilisateur
    form_class = ProfilUtilisateurForm
    success_url = reverse_lazy("profil")
    success_message = "Votre lecteur vidéo préféré a été enregistré."
    login_url = "connexion"

    def get_object(self, queryset=None):
        profil, _ = ProfilUtilisateur.objects.get_or_create(user=self.request.user)
        return profil

    def test_func(self):
        return not self.request.user.is_staff


def inscription(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        utilisateur = form.save()
        login(request, utilisateur)
        return redirect('home')

    return render(request, 'rec117/administration/inscription.html', {'form': form})
