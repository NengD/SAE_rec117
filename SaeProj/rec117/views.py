from django.views.generic import TemplateView
from rec117.models import ConfigurationSite, GenreMusical, Artiste, Lieu, Question, Interview, Extrait

NB_CONTENUS_RECENTS_PAR_DEFAUT = 10


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
