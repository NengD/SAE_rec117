// === Page d'accueil (Mode Lecture) ===
// Les cartes et les menus sont déjà écrits par Django ; ce fichier gère le défilement et les filtres.

// La navbar devient opaque quand on descend
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => navbar.classList.toggle('scrolled', window.scrollY > 50));

// Le hero fait défiler les dernières interviews automatiquement.
const heroCarousel = document.querySelector('[data-hero-carousel]');
if (heroCarousel) {
    const heroSlides = [...heroCarousel.querySelectorAll('[data-hero-slide]')];
    const heroDots = [...heroCarousel.querySelectorAll('[data-hero-dot]')];
    let heroIndex = 0;
    let heroTimer;

    function afficherHero(index) {
        heroIndex = (index + heroSlides.length) % heroSlides.length;
        heroSlides.forEach((slide, position) => {
            const active = position === heroIndex;
            slide.classList.toggle('active', active);
            slide.setAttribute('aria-hidden', String(!active));
        });
        heroDots.forEach((dot, position) => dot.classList.toggle('active', position === heroIndex));
    }

    function relancerHero() {
        window.clearInterval(heroTimer);
        heroTimer = window.setInterval(() => afficherHero(heroIndex + 1), 7000);
    }

    heroCarousel.querySelector('[data-hero-previous]').addEventListener('click', () => {
        afficherHero(heroIndex - 1);
        relancerHero();
    });
    heroCarousel.querySelector('[data-hero-next]').addEventListener('click', () => {
        afficherHero(heroIndex + 1);
        relancerHero();
    });
    heroDots.forEach(dot => dot.addEventListener('click', () => {
        afficherHero(Number(dot.dataset.heroDot));
        relancerHero();
    }));
    relancerHero();
}

// Chaque rangée avance de la largeur d'une carte visible.
document.querySelectorAll('.carousel-shell').forEach(carrousel => {
    const piste = carrousel.querySelector('.carousel');
    const precedent = carrousel.querySelector('.carousel-control-previous');
    const suivant = carrousel.querySelector('.carousel-control-next');

    function mettreAJourControles() {
        precedent.disabled = piste.scrollLeft <= 1;
        suivant.disabled = piste.scrollLeft + piste.clientWidth >= piste.scrollWidth - 1;
    }

    precedent.addEventListener('click', () => {
        piste.scrollBy({left: -piste.clientWidth, behavior: 'smooth'});
    });
    suivant.addEventListener('click', () => {
        piste.scrollBy({left: piste.clientWidth, behavior: 'smooth'});
    });
    piste.addEventListener('scroll', mettreAJourControles, {passive: true});
    window.addEventListener('resize', mettreAJourControles);
    mettreAJourControles();
});

// === Filtres ===
// Chaque carte porte data-artiste, data-lieu et data-genres (voir partials/carte.html).
// On cache les cartes qui ne correspondent pas aux trois menus.
const filtreGenre = document.getElementById('filter-genre');
const filtreLieu = document.getElementById('filter-lieu');
const filtreArtiste = document.getElementById('filter-artiste');
const cartes = document.querySelectorAll('.card');
const rechercheMotsCles = document.getElementById('search-keywords');
const rechercheDateDebut = document.getElementById('search-date-from');
const rechercheDateFin = document.getElementById('search-date-to');

function normaliserRecherche(texte) {
    return texte
        .toLocaleLowerCase('fr-FR')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

function filtrerVideos() {
    const motsCles = (rechercheMotsCles?.value || '')
        .trim()
        .toLocaleLowerCase('fr-FR')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .split(/\s+/)
        .filter(Boolean);
    const dateDebut = rechercheDateDebut?.value || '';
    const dateFin = rechercheDateFin?.value || '';

    cartes.forEach(carte => {
        const contenu = normaliserRecherche(carte.dataset.search || '');
        const date = carte.dataset.date || '';
        const correspond =
            (filtreGenre.value === '' || carte.dataset.genres.split(',').includes(filtreGenre.value)) &&
            (filtreLieu.value === '' || carte.dataset.lieu === filtreLieu.value) &&
            (filtreArtiste.value === '' || carte.dataset.artiste === filtreArtiste.value) &&
            motsCles.every(mot => contenu.includes(mot)) &&
            (!dateDebut || (date && date >= dateDebut)) &&
            (!dateFin || (date && date <= dateFin));

        carte.hidden = !correspond;
    });
}

[filtreGenre, filtreLieu, filtreArtiste].forEach(filtre => filtre.addEventListener('change', filtrerVideos));
[rechercheMotsCles, rechercheDateDebut, rechercheDateFin]
    .filter(Boolean)
    .forEach(filtre => filtre.addEventListener('input', filtrerVideos));

document.getElementById('search-reset')?.addEventListener('click', () => {
    rechercheMotsCles.value = '';
    rechercheDateDebut.value = '';
    rechercheDateFin.value = '';
    filtreGenre.value = '';
    filtreLieu.value = '';
    filtreArtiste.value = '';
    document.querySelectorAll('.chip-btn').forEach(bouton => {
        bouton.classList.toggle('active', bouton.dataset.value === '');
    });
    filtrerVideos();
});
