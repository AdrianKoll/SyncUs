/* =====================================================
   ✅ ROUTER - navegação sem recarregar
   ===================================================== */
const VIEWS_PERMITIDAS = ['dashboard','transactions','history','reports','settings'];
const VIEW_PADRAO = 'dashboard';

window.addEventListener('DOMContentLoaded', async () => {
    const user = await checkAuth();
    if (!user) return;

    // Carrega primeira tela
    await carregarView();

    // Clique nos menus da sidebar
    document.querySelectorAll('.rota').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            window.location.hash = `/${link.dataset.view}`;
            // Fecha sidebar no mobile
            document.getElementById('sidebar')?.classList.remove('aberta');
        });
    });
});

// Quando # da URL mudar → troca a tela
window.addEventListener('hashchange', carregarView);

// Função exportada para usar em botões/gaveta
window.navegar = function (view) {
    window.location.hash = `/${view}`;
};

// Carrega o HTML da view e injeta no <main id="app">
async function carregarView() {
    const hash = window.location.hash.replace('#/', '') || VIEW_PADRAO;
    const view = VIEWS_PERMITIDAS.includes(hash) ? hash : VIEW_PADRAO;
    const app = document.getElementById('app');

    try {
        const res = await fetch(`views/${view}.html`);
        if (!res.ok) throw new Error('Página não encontrada');

        app.innerHTML = await res.text();
        marcarMenuAtivo(view);
        executarScriptsDentroDaView(app);

    } catch (err) {
        app.innerHTML = `
            <div class="card p-5 text-center">
                <h3 class="mb-2">😕 Ops!</h3>
                <p class="text-secondary">${err.message}</p>
            </div>
        `;
    }
}

function marcarMenuAtivo(viewAtiva) {
    document.querySelectorAll('.rota').forEach(link => {
        link.classList.toggle('ativa', link.dataset.view === viewAtiva);
    });
}

// Executa <script> que estiverem dentro da view
function executarScriptsDentroDaView(container) {
    document.querySelectorAll('script[data-syncus-view-script]').forEach(script => script.remove());
    container.querySelectorAll('script').forEach(antigo => {
        const novo = document.createElement('script');
        novo.dataset.syncusViewScript = 'true';
        novo.textContent = antigo.textContent;
        document.body.appendChild(novo);
        antigo.remove();
    });
    document.dispatchEvent(new Event('viewCarregada'));
}