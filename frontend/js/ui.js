// --- UI E EVENTOS ---

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
                
                // Navega
                if (typeof navegarPara === 'function') {
                    navegarPara(view);
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
    // Polling removido: agora usamos WebSockets para atualizações em tempo real
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
        if (elIniciais) elIniciais.textContent = dados.name.substring(0, 2).toUpperCase();

    } catch (err) {
        console.error('💥 Erro ao carregar perfil:', err);
        if (err.message.includes('401') || err.message.includes('token')) {
            window.location.href = 'login.html';
        }
    }
}

// Notificações
async function carregarNotificacoes() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        // CORREÇÃO: A rota no backend está em /api/couple/notifications
        const res = await fetch(`${API_URL}/couple/notifications`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const notificacoes = await res.json();
        
        if (!res.ok) throw new Error('Falha ao carregar notificações');

        // Atualiza o contador (badge)
        const badge = document.getElementById('badgeNotificacoes');
        if (badge) {
            const naoLidas = notificacoes.filter(n => !n.is_read).length;
            badge.textContent = naoLidas;
            badge.style.display = naoLidas > 0 ? 'block' : 'none';
        }

        // Preenche a lista no modal
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
                        <div class="smaller text-muted">${new Date(n.created_at).toLocaleDateString()}</div>
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

    // CORREÇÃO: Remove o '/api' da URL base para o WebSocket conectar na rota correta
    const urlBase = API_URL.replace('/api', '');
    const wsBase = urlBase.replace('http', 'ws' );
    const wsUrl = `${wsBase}/ws/${userId}`;
    
    console.log('🔌 Tentando conectar ao WebSocket:', wsUrl);
    
    try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log('✅ WebSocket Conectado!');
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📩 Mensagem recebida via WS:', data);
                
                // Quando qualquer mensagem chega, atualizamos as notificações
                carregarNotificacoes();
                
                if (typeof showToast === 'function') {
                    showToast('Nova atualização!', 'info');
                }
            } catch (e) {
                console.error('❌ Erro ao processar mensagem do WS:', e);
            }
        };

        socket.onclose = () => {
            console.log('❌ Conexão WebSocket perdida. Tentando reconectar em 5s...');
            socket = null;
            setTimeout(() => conectarWebSocket(userId), 5000);
        };

        socket.onerror = (err) => {
            console.error('💥 Erro no WebSocket:', err);
        };
    } catch (err) {
        console.error('💥 Falha ao iniciar WebSocket:', err);
    }
}
