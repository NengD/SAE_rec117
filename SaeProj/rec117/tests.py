import datetime
import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from . import infos_video
from .models import Artiste, ConfigurationSite, Extrait, GenreMusical, Interview, ProfilUtilisateur, Question


class AnalyseUrlTests(TestCase):
    def test_formats_youtube(self):
        for url in ['https://www.youtube.com/watch?v=1NYQ65FTEC8&t=10s', 'https://youtu.be/1NYQ65FTEC8',
                    'youtube.com/shorts/1NYQ65FTEC8', 'https://m.youtube.com/watch?v=1NYQ65FTEC8',
                    'https://www.youtube.com/embed/1NYQ65FTEC8']:
            self.assertEqual(infos_video.analyser_url(url), ('youtube', '1NYQ65FTEC8'), url)

    def test_formats_vimeo(self):
        self.assertEqual(infos_video.analyser_url('https://vimeo.com/1128762950'), ('vimeo', '1128762950'))
        self.assertEqual(infos_video.analyser_url('https://player.vimeo.com/video/1128762950?h=ab12cd34ef'),
                         ('vimeo', '1128762950/ab12cd34ef'))
        self.assertEqual(infos_video.analyser_url('https://vimeo.com/1128762950/ab12cd34ef'),
                         ('vimeo', '1128762950/ab12cd34ef'))

    def test_url_inconnue(self):
        self.assertEqual(infos_video.analyser_url('https://example.com/video'), (None, None))


PAGE_YOUTUBE = '''<html><meta property="og:title" content="Interview Rivkah">
<script>var ytInitialPlayerResponse = {"videoDetails":{"videoId":"1NYQ65FTEC8","lengthSeconds":"253",
"shortDescription":"Rivkah parle de son univers.\\nBonne \\u00e9coute !","author":"Studio"},
"microformat":{"playerMicroformatRenderer":{"publishDate":"2025-01-15T02:00:00-08:00"}}};</script></html>'''


def faux_reseau(adresse):
    if 'youtube.com/oembed' in adresse:
        return json.dumps({'title': 'Interview Rivkah - rec117', 'author_name': 'Studio Orléans',
                           'thumbnail_url': 'https://i.ytimg.com/vi/1NYQ65FTEC8/hqdefault.jpg'})
    if 'youtube.com/watch' in adresse:
        return PAGE_YOUTUBE
    if 'vimeo.com/api/oembed' in adresse:
        return json.dumps({'title': 'Gontard extrait', 'author_name': 'Studio', 'duration': 95,
                           'description': 'Description Vimeo', 'upload_date': '2025-02-01 10:00:00',
                           'thumbnail_url': 'https://i.vimeocdn.com/video/123-d_295x166'})
    raise OSError('pas de réseau')


@mock.patch.object(infos_video, '_telecharger', side_effect=faux_reseau)
class RecupererInfosTests(TestCase):
    def test_youtube(self, _):
        infos = infos_video.recuperer_infos('https://www.youtube.com/watch?v=1NYQ65FTEC8')
        self.assertEqual(infos['url'], 'https://youtu.be/1NYQ65FTEC8')
        self.assertEqual(infos['titre'], 'Interview Rivkah - rec117')
        self.assertEqual(infos['auteur'], 'Studio Orléans')
        self.assertEqual(infos['duree'], 253)
        self.assertEqual(infos['description'], 'Rivkah parle de son univers.\nBonne écoute !')
        self.assertEqual(infos['date'], datetime.date(2025, 1, 15))
        self.assertIsNone(infos['erreur'])

    def test_vimeo(self, _):
        infos = infos_video.recuperer_infos('https://vimeo.com/1128786403')
        self.assertEqual(infos['duree'], 95)
        self.assertEqual(infos['date'], datetime.date(2025, 2, 1))
        self.assertEqual(infos['description'], 'Description Vimeo')


class SansReseauTests(TestCase):
    @mock.patch.object(infos_video, '_telecharger', side_effect=OSError)
    def test_sans_reseau(self, _):
        infos = infos_video.recuperer_infos('https://youtu.be/1NYQ65FTEC8')
        self.assertIsNone(infos['titre'])
        self.assertTrue(infos['erreur'])
        # La miniature YouTube se déduit de l'identifiant, même sans réseau
        self.assertEqual(infos['miniature'], 'https://i.ytimg.com/vi/1NYQ65FTEC8/hqdefault.jpg')


class AccueilNouveautesTests(TestCase):
    def test_affiche_les_dix_derniers_contenus(self):
        artiste = Artiste.objects.create(nomArtiste='Rivkah')
        question = Question.objects.create(texteQuestion='Présentation')
        interviews = [
            Interview.objects.create(titreInterview=f'Interview {index}', artiste=artiste)
            for index in range(12)
        ]
        extraits = [
            Extrait.objects.create(titreExtrait=f'Extrait {index}', ordreSequence=1,
                                   interview=interview, question=question)
            for index, interview in enumerate(interviews)
        ]

        reponse = self.client.get(reverse('home'))

        self.assertEqual(
            list(reponse.context['dernieres_interviews']),
            list(reversed(interviews[-10:])),
        )
        self.assertEqual(
            list(reponse.context['derniers_extraits']),
            list(reversed(extraits[-10:])),
        )

    def test_seul_un_staff_peut_modifier_la_limite(self):
        url = reverse('admin_configuration')
        reponse = self.client.post(url, {'nombre_videos_carrousel': 6})

        self.assertRedirects(reponse, reverse('admin_connexion') + '?next=' + url)
        self.assertFalse(ConfigurationSite.objects.exists())

        User.objects.create_user('chef', password='x', is_staff=True)
        self.client.login(username='chef', password='x')
        reponse = self.client.post(url, {'nombre_videos_carrousel': 6})

        self.assertRedirects(reponse, reverse('admin_videos'))
        self.assertEqual(ConfigurationSite.objects.get().nombre_videos_carrousel, 6)
class PageProfilTests(TestCase):
    def test_profil_demande_une_connexion_utilisateur(self):
        url = reverse('profil')
        reponse = self.client.get(url)
        self.assertRedirects(reponse, f'{reverse("connexion")}?next={url}')

    def test_utilisateur_standard_voit_ses_informations(self):
        utilisateur = User.objects.create_user(
            username='visiteur', password='x', email='visiteur@example.com',
            first_name='Camille', last_name='Martin',
        )
        self.client.force_login(utilisateur)

        reponse = self.client.get(reverse('profil'))

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, 'visiteur')
        self.assertContains(reponse, 'Camille Martin')
        self.assertNotContains(reponse, 'Adresse e-mail')
        self.assertNotContains(reponse, 'visiteur@example.com')

    def test_utilisateur_peut_enregistrer_son_lecteur_video_prefere(self):
        utilisateur = User.objects.create_user('visiteur', password='x')
        self.client.force_login(utilisateur)

        reponse = self.client.get(reverse('profil'))
        profil = ProfilUtilisateur.objects.get(user=utilisateur)
        self.assertEqual(profil.lecteurPrefere, 'YOUTUBE')
        self.assertContains(reponse, '<option value="YOUTUBE" selected>')
        self.assertContains(reponse, '<option value="VIMEO">')

        reponse = self.client.post(reverse('profil'), {'lecteurPrefere': 'VIMEO'})
        self.assertRedirects(reponse, reverse('profil'))
        profil.refresh_from_db()
        self.assertEqual(profil.lecteurPrefere, 'VIMEO')
        self.assertContains(self.client.get(reverse('profil')), '<option value="VIMEO" selected>')

    def test_page_profil_est_reservee_aux_comptes_non_staff(self):
        staff = User.objects.create_user('chef', password='x', is_staff=True)
        self.client.force_login(staff)

        self.assertEqual(self.client.get(reverse('profil')).status_code, 403)

    def test_lien_profil_visible_uniquement_aux_utilisateurs_standard(self):
        url = reverse('profil')
        utilisateur = User.objects.create_user('visiteur', password='x')
        self.client.force_login(utilisateur)
        self.assertContains(self.client.get(reverse('home')), url)

        staff = User.objects.create_user('chef', password='x', is_staff=True)
        self.client.force_login(staff)
        self.assertNotContains(self.client.get(reverse('home')), url)


@mock.patch.object(infos_video, '_telecharger', side_effect=faux_reseau)
@mock.patch('rec117.templatetags.videos.miniature_oembed', return_value='')
class PageAdministrationTests(TestCase):
    def setUp(self):
        self.rivkah = Artiste.objects.create(nomArtiste='Rivkah')
        self.question = Question.objects.create(texteQuestion='Présentation')
        self.admin = User.objects.create_user('chef', password='x', is_staff=True)

    @override_settings(ADMINISTRATION_OUVERTE=True)
    def test_acces_ouvert_a_tous(self, *_):
        self.assertEqual(self.client.get(reverse('admin_videos')).status_code, 200)
        self.client.post(reverse('admin_ajouter', args=['interview']), {
            'titreInterview': 'Libre', 'artiste': self.rivkah.pk})
        self.assertTrue(Interview.objects.filter(titreInterview='Libre').exists())

    @override_settings(ADMINISTRATION_OUVERTE=False)
    def test_acces_reserve_au_staff(self, *_):
        url = reverse('admin_videos')
        self.assertRedirects(self.client.get(url), reverse('admin_connexion') + '?next=' + url)
        User.objects.create_user('visiteur', password='x')
        self.client.login(username='visiteur', password='x')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.login(username='chef', password='x')
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_bouton_admin_visible_uniquement_au_staff(self, *_):
        url = reverse('admin_videos')
        self.assertNotContains(self.client.get(reverse('mind_map')), url)
        self.client.force_login(User.objects.create_user('visiteur', password='x'))
        self.assertNotContains(self.client.get(reverse('mind_map')), url)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('mind_map')), url)

    def test_inscription_cree_un_compte_non_staff(self, *_):
        from .forms import InscriptionForm

        self.assertEqual(set(InscriptionForm().fields), {'username', 'password1', 'password2'})
        response = self.client.post(reverse('inscription'), {
            'username': 'nouveau',
            'password1': 'MotDePasse-solide-123',
            'password2': 'MotDePasse-solide-123',
            'is_staff': 'on',
            'is_superuser': 'on',
        })
        self.assertRedirects(response, reverse('home'))
        utilisateur = User.objects.get(username='nouveau')
        self.assertFalse(utilisateur.is_staff)
        self.assertFalse(utilisateur.is_superuser)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_compte_standard_peut_se_connecter_et_se_deconnecter(self, *_):
        User.objects.create_user('visiteur', password='MotDePasse-solide-123')
        reponse = self.client.post(reverse('connexion'), {
            'username': 'visiteur',
            'password': 'MotDePasse-solide-123',
        })
        self.assertRedirects(reponse, reverse('home'))
        self.assertTrue(self.client.get(reverse('home')).wsgi_request.user.is_authenticated)

        reponse = self.client.post(reverse('deconnexion'))
        self.assertRedirects(reponse, reverse('home'))
        self.assertFalse(self.client.get(reverse('home')).wsgi_request.user.is_authenticated)

    def test_formulaire_pre_rempli(self, *_):
        self.client.force_login(self.admin)
        interview = Interview.objects.create(titreInterview='Interview Rivkah', artiste=self.rivkah)
        reponse = self.client.get(reverse('admin_ajouter', args=['extrait']),
                                  {'url': 'https://www.youtube.com/watch?v=1NYQ65FTEC8'})
        form = reponse.context['form']
        self.assertEqual(form.initial['titreExtrait'], 'Interview Rivkah - rec117')
        self.assertEqual(form.initial['interview'], interview.pk)  # artiste trouvé dans le titre
        self.assertEqual(form.initial['urlYoutube'], 'https://youtu.be/1NYQ65FTEC8')
        self.assertEqual(form.initial['duree'], 253)
        self.assertContains(reponse, '4:13')
        self.assertNotIn('question', reponse.context['auto'])

    def test_ajout_modification_suppression(self, *_):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('admin_ajouter', args=['interview']), {
            'titreInterview': 'Interview Zed',
            'nouvel_artiste': 'Zed', 'nouveau_lieu': 'Salle', 'ville_nouveau_lieu': 'Tours',
            'pays_nouveau_lieu': 'France',
        })
        self.assertRedirects(reponse, reverse('admin_videos'))
        interview = Interview.objects.get(titreInterview='Interview Zed')
        self.assertEqual(interview.artiste.nomArtiste, 'Zed')
        self.assertEqual(interview.lieu.villeLieu, 'Tours')

        # Extrait : numéro automatique et nouvelle question
        self.client.post(reverse('admin_ajouter', args=['extrait']), {
            'titreExtrait': 'Zed 1', 'urlVimeo': 'https://vimeo.com/1', 'interview': interview.pk,
            'nouvelle_question': 'Pourquoi ?',
        })
        self.client.post(reverse('admin_ajouter', args=['extrait']), {
            'titreExtrait': 'Zed 2', 'urlYoutube': 'https://youtu.be/zed2', 'interview': interview.pk,
            'question': self.question.pk,
        })
        self.assertEqual([e.ordreSequence for e in interview.extraits.all()], [1, 2])

        extrait = Extrait.objects.get(titreExtrait='Zed 2')
        self.client.post(reverse('admin_modifier', args=['extrait', extrait.pk]), {
            'titreExtrait': 'Zed 2 bis', 'urlYoutube': 'https://youtu.be/zed2', 'interview': interview.pk,
            'question': self.question.pk,
            'ordreSequence': 2, 'duree': '1:02:03',
        })
        extrait.refresh_from_db()
        self.assertEqual((extrait.titreExtrait, extrait.duree), ('Zed 2 bis', 3723))
        self.assertEqual(interview.duree_totale, 3723)  # somme des durées des extraits

        # Suppression : confirmation d'abord, puis suppression en cascade des extraits
        url = reverse('admin_supprimer', args=['interview', interview.pk])
        self.assertContains(self.client.get(url), '2 extraits')
        self.assertTrue(Interview.objects.filter(pk=interview.pk).exists())
        self.client.post(url)
        self.assertFalse(Interview.objects.filter(pk=interview.pk).exists())
        self.assertFalse(Extrait.objects.exists())

    def test_interviews_et_leurs_extraits(self, *_):
        self.client.force_login(self.admin)
        interview = Interview.objects.create(titreInterview='Interview Rivkah', artiste=self.rivkah)
        Extrait.objects.create(titreExtrait='Rivkah 1', ordreSequence=1, urlYoutube='https://youtu.be/un',
                               interview=interview, question=self.question)
        page = self.client.get(reverse('admin_videos')).content.decode()
        # L'extrait est dans la ligne cachée qui suit son interview
        self.assertLess(page.index(f'id="extraits-{interview.pk}" hidden'), page.index('Rivkah 1'))
        # « Ajouter un extrait à cette interview » pré-sélectionne l'interview
        reponse = self.client.get(reverse('admin_ajouter', args=['extrait']), {'interview': interview.pk})
        self.assertEqual(str(reponse.context['form'].initial['interview']), str(interview.pk))

    def test_nouveau_genre(self, *_):
        self.client.force_login(self.admin)
        self.client.post(reverse('admin_ajouter', args=['interview']), {
            'titreInterview': 'Interview Rivkah', 'artiste': self.rivkah.pk,
            'nouveau_genre': 'Électro', 'couleur_nouveau_genre': '#1DB954',
        })
        genre = GenreMusical.objects.get(nomGenre='Électro')
        self.assertEqual(genre.codeCouleur, '#1DB954')
        self.assertIn(genre, self.rivkah.genres.all())  # ajouté à l'artiste choisi
        # Couleur invalide : refusée
        reponse = self.client.post(reverse('admin_ajouter', args=['interview']), {
            'titreInterview': 'X', 'artiste': self.rivkah.pk, 'nouveau_genre': 'Jazz', 'couleur_nouveau_genre': 'rouge',
        })
        self.assertIn('couleur_nouveau_genre', reponse.context['form'].errors)


    def test_erreurs(self, *_):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse('admin_ajouter', args=['interview']), {'titreInterview': 'X'})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('artiste', reponse.context['form'].errors)
        self.assertFalse(Interview.objects.exists())

        # Un extrait doit avoir sa propre vidéo
        reponse = self.client.post(reverse('admin_ajouter', args=['extrait']), {'titreExtrait': 'Y'})
        self.assertIn('urlYoutube', reponse.context['form'].errors)
        self.assertFalse(Extrait.objects.exists())


@mock.patch('rec117.templatetags.videos.miniature_oembed', return_value='')
class PlaylistTests(TestCase):
    def test_interview_en_playlist(self, _):
        artiste = Artiste.objects.create(nomArtiste='Rivkah')
        question = Question.objects.create(texteQuestion='Présentation')
        interview = Interview.objects.create(titreInterview='Interview Rivkah', artiste=artiste)
        for ordre, video in [(2, 'https://youtu.be/deux'), (1, 'https://youtu.be/un')]:
            Extrait.objects.create(titreExtrait=f'Extrait {ordre}', ordreSequence=ordre, urlYoutube=video,
                                   interview=interview, question=question)
        page = self.client.get(reverse('home')).content.decode()
        self.assertIn('Lancer la playlist', page)
        # Les extraits de la playlist sont dans l'ordre de l'interview
        self.assertLess(page.index('data-youtube="https://youtu.be/un"'), page.index('data-youtube="https://youtu.be/deux"'))
