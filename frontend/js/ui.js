// --- UI E EVENTOS ---

// Variáveis globais para controlar as instâncias dos gráficos e evitar erro de Canvas
let instanciaChartRosca = null;
let instanciaChartLinha = null;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🖥️ UI carregada');
    
    // Inicializar componentes
    setupSidebar();
    setupNotifications();
    
    // Carregar dados iniciais
    carregarPerfilUsuario();
    carregarNotificacoes();
});

// Sidebar e Navegação
function setupSidebar() {
    const btnToggle = document.getElementById('btnToggleSidebar');
    const sidebar = document.querySelector('.sidebar');
    const main = document.querySelector('.main-content');

    if (btnToggle && sidebar) {
        btnToggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            if (main) main.classList.toggle('active');
        });
    }

    // Links do menu
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.getAttribute('data-view');
            if (view) {
                // Remove active de todos
                links.forEach(l => l.classList.remove('active'));
                // Adiciona no clicado
                link.classList.add('active');
                
                // Navega usando o router.js
                if (typeof navegar === 'function') {
                    navegar(view);
                }
            }
        });
    });
}

// Notificações
function setupNotifications() {
    const btn = document.getElementById('btnNotificacoes');
    if (btn) {
        btn.addEventListener('click', () => {
            const modalElement = document.getElementById('modalNotificacoes');
            if (modalElement) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
                carregarNotificacoes();
            }
        });
    }
}

// Perfil do Usuário
async function carregarPerfilUsuario() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const dados = await res.json();
        if (!res.ok) throw new Error(dados.detail || 'Erro ao carregar perfil');

        localStorage.setItem('user', JSON.stringify(dados));
        
        // Inicia a conexão em tempo real após obter o ID do usuário
        conectarWebSocket(dados.id);

        // Atualiza na tela
        const elNome = document.getElementById('userNome');
        const elEmail = document.getElementById('userEmail');
        const elIniciais = document.getElementById('userIniciais');

        if (elNome) elNome.textContent = dados.name;
        if (elEmail) elEmail.textContent = dados.email;
        if (elIniciais) elIniciais.textContent = iniciaisDoNome(dados.name);

    } catch (err) {
        console.error('💥 Erro ao carregar perfil:', err);
        if (err.message.includes('401') || err.message.includes('token')) {
            logout();
        }
    }
}

// Notificações
async function carregarNotificacoes() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        // A rota no backend está em /api/couple/notifications
        const res = await fetch(`${API_URL}/couple/notifications`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const notificacoes = await res.json();
        if (!res.ok) throw new Error('Falha ao carregar notificações');

        const badge = document.getElementById('badgeNotificacoes');
        if (badge) {
            const naoLidas = notificacoes.filter(n => !n.is_read).length;
            badge.textContent = naoLidas;
            badge.style.display = naoLidas > 0 ? 'block' : 'none';
        }

        const lista = document.getElementById('listaNotificacoes');
        if (lista) {
            if (notificacoes.length === 0) {
                lista.innerHTML = '<div class="text-center py-4 text-secondary">Nenhuma notificação</div>';
                return;
            }

            lista.innerHTML = notificacoes.map(n => `
                <div class="notification-item ${n.is_read ? '' : 'unread'} p-3 border-bottom">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <div class="fw-bold small">${n.title}</div>
                            <div class="text-secondary smaller">${n.message}</div>
                        </div>
                        <div class="smaller text-muted">${formatDate(n.created_at)}</div>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('💥 Erro ao carregar notificações:', err);
    }
}

// --- LÓGICA DE TEMPO REAL (WEBSOCKET) ---
let socket = null;

function conectarWebSocket(userId) {
    if (socket) return;

    // Remove o '/api' da URL base para o WebSocket conectar na rota correta
    const urlBase = API_URL.replace('/api', '');
    const wsBase = urlBase.replace('http', 'ws' );
    const wsUrl = `${wsBase}/ws/${userId}`;
    
    console.log('🔌 Tentando conectar ao WebSocket:', wsUrl);
    
    try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => console.log('✅ WebSocket Conectado!');

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📩 Mensagem recebida via WS:', data);
                carregarNotificacoes();
                if (typeof showToast === 'function') showToast('Nova atualização!', 'info');
            } catch (e) {
                console.error('❌ Erro ao processar mensagem do WS:', e);
            }
        };

        socket.onclose = () => {
            console.log('❌ Conexão WebSocket perdida. Tentando reconectar em 5s...');
            socket = null;
            setTimeout(() => conectarWebSocket(userId), 5000);
        };

        socket.onerror = (err) => console.error('💥 Erro no WebSocket:', err);
    } catch (err) {
        console.error('💥 Falha ao iniciar WebSocket:', err);
    }
}

// =====================================================
// ✅ INTEGRAÇÃO FINANCEIRA - Dashboard e Lançamentos
// =====================================================

document.addEventListener('viewCarregada', () => {
    const hash = window.location.hash.replace('#/', '') || 'dashboard';
    
    if (hash === 'dashboard') {
        inicializarDashboard();
    } else if (hash === 'transactions') {
        // inicializarTransactions(); // Implementar futuramente
    }
});

async function inicializarDashboard() {
    console.log('📊 Sincronizando Dashboard...');
    const token = localStorage.getItem('token');
    
    try {
        const res = await fetch(`${API_URL}/transactions/dashboard`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!res.ok) {
            const erro = await res.json();
            throw new Error(erro.detail || 'Erro na API');
        }
        
        const dados = await res.json();

        // 1. Cards de Resumo
        const preencherCard = (seletor, valor) => {
            const el = document.querySelector(seletor);
            if (el) el.textContent = valor;
        };

        preencherCard('.card-azul .valor', formatCurrency(dados.summary.total_balance));
        preencherCard('.card-verde .valor', formatCurrency(dados.summary.monthly_income));
        preencherCard('.card-vermelho .valor', formatCurrency(dados.summary.monthly_expenses));
        preencherCard('.card-roxo .valor', dados.summary.debt_summary);

        // 2. Lista de Transações Recentes
        const containerRecentes = document.querySelector('.ultimas-transacoes-lista');
        if (containerRecentes && dados.recent) {
            if (dados.recent.length === 0) {
                containerRecentes.innerHTML = '<div class="text-center p-3 text-muted">Nenhum lançamento este mês.</div>';
            } else {
                containerRecentes.innerHTML = dados.recent.map(t => `
                    <div class="transacao-item d-flex align-items-center justify-content-between p-2 mb-2 border-bottom">
                        <div class="d-flex align-items-center">
                            <div class="icone-cat me-3 ${t.type === 'entrada' ? 'text-success' : 'text-danger'}">
                                <i class="fa-solid ${t.type === 'entrada' ? 'fa-arrow-down' : 'fa-arrow-up'}"></i>
                            </div>
                            <div>
                                <div class="fw-bold small">${t.description}</div>
                                <div class="text-muted smaller">${t.category} | ${t.date}</div>
                            </div>
                        </div>
                        <div class="fw-bold small ${t.type === 'entrada' ? 'text-success' : 'text-danger'}">
                            ${t.type === 'entrada' ? '+' : '-'} ${formatCurrency(t.amount)}
                        </div>
                    </div>
                `).join('');
            }
        }

        // 3. Gráficos
        if (typeof Chart !== 'undefined') {
            renderizarGraficosDashboard(dados);
        }

    } catch (err) {
        console.error('💥 Erro ao sincronizar Dashboard:', err);
        showToast('Erro de sincronização: ' + err.message, 'danger');
    }
}

function renderizarGraficosDashboard(dados) {
    // --- Gráfico de Rosca ---
    const ctxRosca = document.getElementById('graficoCategorias')?.getContext('2d');
    if (ctxRosca && dados.categories.length > 0) {
        if (instanciaChartRosca) instanciaChartRosca.destroy();
        
        instanciaChartRosca = new Chart(ctxRosca, {
            type: 'doughnut',
            data: {
                labels: dados.categories.map(c => c.name),
                datasets: [{
                    data: dados.categories.map(c => c.value),
                    backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A78BFA']
                }]
            },
            options: { cutout: '70%', plugins: { legend: { display: false } } }
        });
    }

    // --- Gráfico de Linha ---
    const ctxLinha = document.getElementById('graficoFluxo')?.getContext('2d');
    if (ctxLinha) {
        if (instanciaChartLinha) instanciaChartLinha.destroy();

        instanciaChartLinha = new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dados.chart_data.labels,
                datasets: [
                    { label: 'Entradas', data: dados.chart_data.income, borderColor: '#10B981', tension: 0.4 },
                    { label: 'Saídas', data: dados.chart_data.expenses, borderColor: '#EF4444', tension: 0.4 }
                ]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: { legend: { display: false } } 
            }
        });
    }
}
