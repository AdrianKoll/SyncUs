/* =====================================================
   ✅ ROUTER - navegação sem recarregar
   ===================================================== */
const VIEWS_PERMITIDAS = ['dashboard','transactions','history','reports','settings'];
const VIEW_PADRAO = 'dashboard';
let carregamentoViewAtual = 0;
let controladorViewAtual = null;

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
    window.__syncusViewToken = (window.__syncusViewToken || 0) + 1;
    const idCarregamento = ++carregamentoViewAtual;
    controladorViewAtual?.abort();
    controladorViewAtual = new AbortController();
    fecharControlesAbertos();
    const hash = window.location.hash.replace('#/', '') || VIEW_PADRAO;
    const view = VIEWS_PERMITIDAS.includes(hash) ? hash : VIEW_PADRAO;
    const app = document.getElementById('app');
    if (!app) return;

    try {
        const res = await fetch(`views/${view}.html?v=${Date.now()}`, {
            cache: 'no-store',
            signal: controladorViewAtual.signal,
        });
        if (!res.ok) throw new Error('Página não encontrada');
        const html = await res.text();
        if (idCarregamento !== carregamentoViewAtual) return;

        app.innerHTML = html;
        marcarMenuAtivo(view);
        await executarScriptsDentroDaView(app);

    } catch (err) {
        if (err.name === 'AbortError' || idCarregamento !== carregamentoViewAtual) return;
        app.innerHTML = `
            <div class="card p-5 text-center">
                <h3 class="mb-2">😕 Ops!</h3>
                <p class="text-secondary">${err.message}</p>
            </div>
        `;
    }
}

function fecharControlesAbertos() {
    const elementoAtivo = document.activeElement;
    if (elementoAtivo && elementoAtivo !== document.body && typeof elementoAtivo.blur === 'function') {
        elementoAtivo.blur();
    }

    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        const toggle = menu.previousElementSibling;
        if (toggle && window.bootstrap?.Dropdown) {
            window.bootstrap.Dropdown.getOrCreateInstance(toggle).hide();
        } else {
            menu.classList.remove('show');
        }
    });
}

function marcarMenuAtivo(viewAtiva) {
    document.querySelectorAll('.rota').forEach(link => {
        link.classList.toggle('ativa', link.dataset.view === viewAtiva);
    });
}

// Executa <script> que estiverem dentro da view
async function executarScriptsDentroDaView(container) {
    document.querySelectorAll('script[data-syncus-view-script]').forEach(script => script.remove());
    const carregamentos = [];

    container.querySelectorAll('script').forEach(antigo => {
        const novo = document.createElement('script');
        novo.dataset.syncusViewScript = 'true';
        for (const atributo of antigo.attributes) {
            novo.setAttribute(atributo.name, atributo.value);
        }
        novo.textContent = antigo.textContent;

        if (novo.src || novo.type === 'module') {
            carregamentos.push(new Promise((resolve, reject) => {
                novo.addEventListener('load', resolve, { once: true });
                novo.addEventListener('error', () => reject(new Error(`Não foi possível carregar ${novo.src || 'o módulo da view'}`)), { once: true });
            }));
        } else {
            carregamentos.push(Promise.resolve());
        }

        document.body.appendChild(novo);
        antigo.remove();
    });

    await Promise.all(carregamentos);
    document.dispatchEvent(new Event('viewCarregada'));
}