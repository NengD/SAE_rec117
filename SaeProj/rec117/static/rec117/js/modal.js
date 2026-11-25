// === Fenêtre modale d'une vidéo ===
// Partagée par la page d'accueil et la carte mentale.
// Toutes les fiches sont déjà écrites dans la page par Django (partials/fiche_*.html), cachées.
// Ce fichier affiche la bonne et lance la vidéo dans un lecteur YouTube ou Vimeo.
// Une interview complète n'a pas de vidéo : c'est une playlist qui enchaîne ses extraits.

const modal = document.getElementById('video-modal');

// Arrête la vidéo en cours : on retire le lecteur et on remet la miniature
function arreterVideo() {
    modal.querySelectorAll('.lecteur-video').forEach(lecteur => lecteur.remove());
    modal.querySelectorAll('.en-lecture').forEach(entete => entete.classList.remove('en-lecture'));
    modal.querySelectorAll('.playlist-item.en-cours').forEach(item => item.classList.remove('en-cours'));
}

// Affiche la fiche demandée, par exemple ouvrirFiche('extrait-3') affiche #fiche-extrait-3
function ouvrirFiche(nom) {
    arreterVideo();
    modal.querySelectorAll('.fiche').forEach(fiche => { fiche.hidden = true; });
    document.getElementById(`fiche-${nom}`).hidden = false;
    modal.querySelector('.modal-content').scrollTop = 0;
    modal.classList.add('active');
    document.body.classList.add('modal-ouverte');
}

function fermerModal() {
    arreterVideo();
    modal.classList.remove('active');
    document.body.classList.remove('modal-ouverte');
}

// Tout élément qui porte data-fiche ouvre la fiche correspondante au clic :
// cartes, bouton de l'interview à la une, bifurcations, éléments de la carte mentale.
// S'il porte aussi data-debut (bifurcation « même question »), la vidéo démarre à ce timecode.
document.addEventListener('click', e => {
    const element = e.target.closest('[data-fiche]');
    if (!element) return;
    ouvrirFiche(element.dataset.fiche);
    if (element.dataset.debut !== undefined) {
        lancerExtrait(document.getElementById(`fiche-${element.dataset.fiche}`), element.dataset.debut);
    }
});

// Transforme l'adresse d'une vidéo en adresse de lecteur intégrable dans la page
//   https://youtu.be/ID ou https://www.youtube.com/watch?v=ID  →  https://www.youtube.com/embed/ID
//   https://vimeo.com/ID                                       →  https://player.vimeo.com/video/ID
// enablejsapi=1 permet à la playlist de savoir quand une vidéo YouTube est finie.
function adresseLecteur(lecteur, adresse, debut) {
    if (lecteur === 'youtube') {
        const id = adresse.includes('watch?v=')
            ? adresse.split('watch?v=')[1].split('&')[0]
            : adresse.split('/').pop().split('?')[0];
        return `https://www.youtube.com/embed/${id}?autoplay=1&enablejsapi=1&start=${debut}`;
    }
    const id = adresse.split('/').pop().split('?')[0];
    return `https://player.vimeo.com/video/${id}?autoplay=1#t=${debut}s`;
}

// Crée le lecteur (une iframe YouTube ou Vimeo) à la place de la miniature, en haut de la fiche
function afficherLecteur(entete, lecteur, adresse, debut) {
    arreterVideo();
    const iframe = document.createElement('iframe');
    iframe.className = 'lecteur-video';
    iframe.src = adresseLecteur(lecteur, adresse, debut || 0);
    iframe.allow = 'autoplay; fullscreen; picture-in-picture';
    iframe.allowFullscreen = true;
    // YouTube refuse de lire la vidéo si la page ne transmet pas son adresse (erreur 153)
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    entete.classList.add('en-lecture');
    entete.appendChild(iframe);
    return iframe;
}

// Lance la vidéo d'une fiche d'extrait à partir de debut (en secondes),
// avec le lecteur choisi dans la liste (l'adresse est dans les attributs data-* du bouton « Lancer »)
function lancerExtrait(fiche, debut) {
    const bouton = fiche.querySelector('.btn-lancer');
    if (!bouton) return; // fiche d'interview : pas de vidéo à elle
    const lecteur = fiche.querySelector('.choix-lecteur').value; // 'youtube' ou 'vimeo'
    const adresse = bouton.dataset[lecteur];
    if (!adresse) {
        alert(`Pas de vidéo ${lecteur} pour cette fiche.`);
        return;
    }
    afficherLecteur(fiche.querySelector('.modal-header'), lecteur, adresse, debut);
    // La question en cours est mise en valeur dans la liste
    fiche.querySelectorAll('.btn-timecode').forEach(b => b.classList.toggle('actif', b.dataset.debut === String(debut)));
    fiche.querySelector('.modal-header').scrollIntoView({ behavior: 'smooth' });
}

// Bouton « Lancer la vidéo » d'un extrait : depuis le début
modal.querySelectorAll('.btn-lancer').forEach(bouton => {
    bouton.addEventListener('click', () => lancerExtrait(bouton.closest('.fiche'), bouton.dataset.debut));
});

// Questions de la vidéo : un clic relance la vidéo au timecode de la question
modal.querySelectorAll('.btn-timecode').forEach(bouton => {
    bouton.addEventListener('click', () => lancerExtrait(bouton.closest('.fiche'), bouton.dataset.debut));
});

// === Playlist d'une interview complète ===

// Appelle suite() quand la vidéo du lecteur est terminée.
// Utilise les API officielles chargées dans video_modal.html. Si elles ne sont pas chargées,
// la playlist ne passe pas toute seule à l'extrait suivant : il reste le bouton « Suivant ».
function quandVideoFinie(iframe, lecteur, suite) {
    if (lecteur === 'vimeo' && window.Vimeo) {
        new Vimeo.Player(iframe).on('ended', suite);
    }
    if (lecteur === 'youtube' && window.YT && YT.Player) {
        new YT.Player(iframe, {
            events: { onStateChange: e => { if (e.data === YT.PlayerState.ENDED) suite(); } },
        });
    }
}

// Lit l'extrait n°index de la playlist de la fiche, puis enchaîne sur le suivant
function lireDansPlaylist(fiche, index) {
    const extraits = fiche.querySelectorAll('.playlist-item');
    if (index < 0 || index >= extraits.length) {
        arreterVideo(); // fin de la playlist : on remet la miniature
        return;
    }
    const extrait = extraits[index];

    // Lecteur choisi, ou l'autre plateforme si l'extrait n'existe pas sur celle-là
    let lecteur = fiche.querySelector('.choix-lecteur').value;
    if (!extrait.dataset[lecteur]) lecteur = lecteur === 'youtube' ? 'vimeo' : 'youtube';
    if (!extrait.dataset[lecteur]) {
        lireDansPlaylist(fiche, index + 1); // extrait sans vidéo : on le saute
        return;
    }

    const iframe = afficherLecteur(fiche.querySelector('.modal-header'), lecteur, extrait.dataset[lecteur], 0);
    extrait.classList.add('en-cours');
    fiche.dataset.index = index;
    quandVideoFinie(iframe, lecteur, () => lireDansPlaylist(fiche, index + 1));
}

// Boutons de la playlist : lancer depuis le début, un extrait précis, précédent, suivant
modal.querySelectorAll('.fiche').forEach(fiche => {
    if (!fiche.querySelector('.playlist')) return;
    const indexActuel = () => Number(fiche.dataset.index || 0);

    fiche.querySelector('.btn-playlist').addEventListener('click', () => lireDansPlaylist(fiche, 0));
    fiche.querySelectorAll('.playlist-lire').forEach((bouton, index) => {
        bouton.addEventListener('click', () => lireDansPlaylist(fiche, index));
    });
    fiche.querySelector('.playlist-precedent').addEventListener('click', () => lireDansPlaylist(fiche, Math.max(indexActuel() - 1, 0)));
    fiche.querySelector('.playlist-suivant').addEventListener('click', () => lireDansPlaylist(fiche, indexActuel() + 1));
});

document.getElementById('modal-close').addEventListener('click', fermerModal);

// Un clic sur le fond sombre ferme la modale
modal.addEventListener('click', e => {
    if (e.target === modal) fermerModal();
});