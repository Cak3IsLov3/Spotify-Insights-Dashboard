const GREEN = '#1db954';
const GREENS = [
    '#1db954','#1ed760','#17a44a','#15883d','#2ee66b',
    '#45e87e','#5ceb91','#74eda4','#8bf0b7','#a3f2ca',
    '#1aa34a','#148f3f','#0f7a34','#0a6629','#06511e',
];

let artistsData = null;
let tracksData = null;
let artistsChart = null;
let genresChart = null;
let currentRange = 'short_term';

async function fetchJSON(url) {
    try {
        const resp = await fetch(url);
        if (resp.status === 401) {
            window.location.href = '/';
            return null;
        }
        const data = await resp.json();
        console.log('fetchJSON', url, data);
        return data;
    } catch (e) {
        console.error('Fetch error:', url, e);
        return null;
    }
}

function renderArtistsChart(artists) {
    console.log('renderArtistsChart called with', artists?.length, 'artists');
    const ctx = document.getElementById('artists-chart');
    if (!ctx) { console.error('No artists-chart canvas'); return; }

    if (!artists || artists.length === 0) {
        // Show message on empty canvas
        const c = ctx.getContext('2d');
        if (artistsChart) { artistsChart.destroy(); artistsChart = null; }
        c.clearRect(0, 0, ctx.width, ctx.height);
        c.font = '14px -apple-system, sans-serif';
        c.fillStyle = '#727272';
        c.textAlign = 'center';
        c.fillText('No artist data for this period', ctx.width / 2, ctx.height / 2);
        return;
    }

    const top10 = artists.slice(0, 10);
    if (artistsChart) artistsChart.destroy();

    // Use popularity if available, otherwise use reverse ranking as score
    const hasPopularity = top10.some(a => a.popularity > 0);
    const data = hasPopularity
        ? top10.map(a => a.popularity)
        : top10.map((_, i) => top10.length - i);

    artistsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10.map(a => a.name),
            datasets: [{
                label: hasPopularity ? 'Popularity' : 'Ranking',
                data: data,
                backgroundColor: GREEN,
                borderRadius: 6,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: {
                    max: hasPopularity ? 100 : top10.length,
                    grid: { color: '#333' },
                    ticks: { color: '#b3b3b3' }
                },
                y: { grid: { display: false }, ticks: { color: '#fff', font: { size: 12 } } }
            }
        }
    });
}

function renderGenresChart(genres) {
    const ctx = document.getElementById('genres-chart');
    if (!ctx) return;
    const c = ctx.getContext('2d');
    if (genresChart) { genresChart.destroy(); genresChart = null; }

    if (!genres || genres.length === 0) {
        c.clearRect(0, 0, ctx.width, ctx.height);
        c.font = '14px -apple-system, sans-serif';
        c.fillStyle = '#727272';
        c.textAlign = 'center';
        c.fillText('Genre data not available in Dev Mode', ctx.width / 2, ctx.height / 2);
        return;
    }

    const top10 = genres.slice(0, 10);
    genresChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: top10.map(g => g.name),
            datasets: [{
                data: top10.map(g => g.count),
                backgroundColor: GREENS.slice(0, top10.length),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#b3b3b3', padding: 12, font: { size: 11 } }
                }
            }
        }
    });
}

function renderTracks(tracks) {
    const container = document.getElementById('tracks-list');
    if (!container) return;
    console.log('renderTracks called with', tracks?.length, 'tracks');

    if (!tracks || !tracks.length) {
        container.innerHTML = '<p class="loading">No tracks found for this period.</p>';
        return;
    }
    container.innerHTML = tracks.slice(0, 20).map((t, i) => {
        const albumImages = t.album && t.album.images ? t.album.images : [];
        const cover = albumImages.length > 0 ? albumImages[albumImages.length - 1].url : '';
        const artistNames = (t.artists || []).map(a => a.name).join(', ');
        const link = (t.external_urls && t.external_urls.spotify) ? t.external_urls.spotify : '#';
        return `
        <div class="track-item">
            <span class="track-rank">${i + 1}</span>
            ${cover ? `<img class="track-cover" src="${cover}" alt="">` : '<div class="track-cover"></div>'}
            <div class="track-info">
                <div class="track-name">${t.name}</div>
                <div class="track-artist">${artistNames}</div>
            </div>
            <a class="track-link" href="${link}" target="_blank" rel="noopener">Open &#8599;</a>
        </div>`;
    }).join('');
}

function updateView() {
    console.log('updateView', currentRange, 'artistsData:', !!artistsData, 'tracksData:', !!tracksData);
    if (artistsData) {
        const artists = artistsData[currentRange] || [];
        console.log('Artists for range:', artists.length);
        renderArtistsChart(artists);
    }
    if (tracksData) {
        const tracks = tracksData[currentRange] || [];
        console.log('Tracks for range:', tracks.length);
        renderTracks(tracks);
    }
}

async function init() {
    console.log('Dashboard init starting...');

    const [artists, tracks, insights] = await Promise.all([
        fetchJSON('/api/top/artists'),
        fetchJSON('/api/top/tracks'),
        fetchJSON('/api/insights'),
    ]);

    console.log('Fetched artists:', artists);
    console.log('Fetched tracks:', tracks);
    console.log('Fetched insights:', insights);

    artistsData = artists;
    tracksData = tracks;

    // Insights cards
    if (insights) {
        const obscEl = document.getElementById('obscurity-score');
        const divEl = document.getElementById('genre-diversity');
        const mainEl = document.getElementById('mainstream-pct');

        if (obscEl) obscEl.textContent = insights.obscurity_score != null ? insights.obscurity_score : 'N/A';
        if (divEl) divEl.textContent = insights.genre_diversity != null ? insights.genre_diversity : '0';
        if (mainEl) mainEl.textContent = (insights.mainstream_percentage != null ? insights.mainstream_percentage : 0) + '%';
        renderGenresChart(insights.top_genres || []);
    }

    updateView();

    // Time range buttons
    document.querySelectorAll('.btn-time').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-time').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRange = btn.dataset.range;
            updateView();
        });
    });

    console.log('Dashboard init complete');
}

init();
