/* =====================================================
   UI GLOBAL - perfil, notificações, WebSocket e dashboard
   ===================================================== */

let instanciaChartRosca = null;
let instanciaChartLinha = null;
let socket = null;
let socketConnectionKey = null;


document.addEventListener('DOMContentLoaded', () => {
    setupSidebar();
    setupNotifications();
    carregarPerfilUsuario();
    carregarNotificacoes();
    if (!window.__syncusNotificationsInterval) {
        window.__syncusNotificationsInterval = setInterval(carregarNotificacoes, 30000);
    }
});


function setupSidebar() {
    const btnToggle = document.getElementById('btnMenu');
    const sidebar = document.getElementById('sidebar');

    if (btnToggle && sidebar) {
        btnToggle.addEventListener('click', () => {
            sidebar.classList.toggle('aberta');
        });
    }

    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            document.querySelectorAll('.nav-link').forEach(item => item.classList.remove('active'));
            link.classList.add('active');
            sidebar?.classList.remove('aberta');
        });
    });
}


function setupNotifications() {
    const button = document.getElementById('btnSininho');
    button?.addEventListener('click', carregarNotificacoes);

    document.getElementById('marcarTodasLidas')?.addEventListener('click', async event => {
        event.preventDefault();
        try {
            await apiRequest('/couple/notifications/read-all', { method: 'PUT' });
            await carregarNotificacoes();
        } catch (error) {
            showToast(handleApiError(error, 'Não foi possível atualizar as notificações.'), 'danger');
        }
    });
}


async function carregarPerfilUsuario() {
    if (!getStoredToken()) return;

    try {
        const dados = await apiRequest('/users/me');
        localStorage.setItem('user', JSON.stringify(dados));
        conectarWebSocket();

        document.querySelectorAll('#userNome, #perfilNome, #gavetaNome').forEach(element => {
            element.textContent = dados.name;
        });
        document.querySelectorAll('#userEmail, #gavetaEmail').forEach(element => {
            element.textContent = dados.email;
        });
        document.querySelectorAll('#userIniciais, #perfilFoto').forEach(element => {
            element.textContent = iniciaisDoNome(dados.name);
        });
    } catch (error) {
        if (isAuthError(error)) logout();
        else console.error('Erro ao carregar perfil:', error);
    }
}


async function carregarNotificacoes() {
    if (!getStoredToken()) return;

    try {
        const notificacoes = await apiRequest('/couple/notifications');
        const naoLidas = notificacoes.filter(item => !item.is_read).length;
        const badge = document.getElementById('badgeNotificacoes');
        if (badge) {
            badge.textContent = naoLidas;
            badge.style.display = naoLidas > 0 ? 'block' : 'none';
        }

        const lista = document.getElementById('listaNotificacoes');
        if (!lista) return;
        const cabecalho = lista.querySelector(':scope > li:first-child');
        const conteudo = notificacoes.length
            ? notificacoes.map(notification => `
                <li class="notification-item ${notification.is_read ? '' : 'unread'} p-3 border-bottom">
                    <div class="d-flex justify-content-between align-items-start gap-2">
                        <div>
                            <div class="fw-bold small">${escapeHtml(notification.title)}</div>
                            <div class="text-secondary smaller">${escapeHtml(notification.message)}</div>
                            ${notification.type === 'invite_income' && !notification.is_read ? `
                                <div class="mt-2 d-flex gap-2">
                                    <button class="btn btn-sm btn-success" onclick="responderConvite(${notification.related_id}, 'accept')">Aceitar</button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="responderConvite(${notification.related_id}, 'reject')">Recusar</button>
                                </div>
                            ` : ''}
                        </div>
                        <div class="smaller text-muted">${formatDate(notification.created_at)}</div>
                    </div>
                </li>
            `).join('')
            : '<li class="p-4 text-center text-secondary small">Nenhuma notificação</li>';

        lista.innerHTML = '';
        if (cabecalho) lista.appendChild(cabecalho);
        lista.insertAdjacentHTML('beforeend', conteudo);
    } catch (error) {
        if (isAuthError(error)) logout();
        else console.error('Erro ao carregar notificações:', error);
    }
}


window.responderConvite = async function (inviteId, action) {
    try {
        const response = await apiRequest(`/couple/invite/${inviteId}/${action}`, { method: 'POST' });
        showToast(response.mensagem || 'Convite atualizado.', 'success');
        await carregarNotificacoes();
        await carregarPerfilUsuario();
        if (typeof carregarParceiro === 'function') await carregarParceiro();
        if (typeof inicializarDashboard === 'function') await inicializarDashboard();
    } catch (error) {
        showToast(handleApiError(error, 'Não foi possível responder ao convite.'), 'danger');
    }
};


function conectarWebSocket() {
    const token = getStoredToken();
    if (!token) return;

    if (socket && socketConnectionKey === token) return;
    if (socket) {
        socket.onclose = null;
        socket.close();
    }

    socketConnectionKey = token;
    const urlBase = API_URL.replace(/\/api\/?$/, '');
    const wsBase = urlBase.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/ws/?token=${encodeURIComponent(token)}`;
    const currentSocket = new WebSocket(wsUrl);
    socket = currentSocket;

    currentSocket.onopen = () => console.log('WebSocket conectado à sala autenticada.');
    currentSocket.onmessage = () => carregarNotificacoes();
    currentSocket.onclose = event => {
        if (socket !== currentSocket) return;

        socket = null;
        socketConnectionKey = null;
        if (event.code !== 1008 && getStoredToken() === token) {
            setTimeout(() => conectarWebSocket(), 5000);
        }
    };
    currentSocket.onerror = error => console.warn('WebSocket indisponível:', error);
}


document.addEventListener('viewCarregada', () => {
    const hash = window.location.hash.replace('#/', '') || 'dashboard';
    if (hash === 'dashboard') inicializarDashboard();
    if (hash === 'transactions' && typeof inicializarTransactions === 'function') inicializarTransactions();
    if (hash === 'history' && typeof inicializarHistorico === 'function') inicializarHistorico();
    if (hash === 'reports' && typeof inicializarRelatorios === 'function') inicializarRelatorios();
});


async function inicializarDashboard() {
    const selectMonth = document.getElementById('dashboardMonth');
    const now = new Date();
    if (selectMonth && !selectMonth.dataset.bound) {
        selectMonth.value = String(now.getMonth() + 1);
        selectMonth.addEventListener('change', inicializarDashboard);
        selectMonth.dataset.bound = 'true';
    }
    const month = Number(selectMonth?.value || now.getMonth() + 1);
    const year = now.getFullYear();

    try {
        const dados = await apiRequest(`/transactions/dashboard?year=${year}&month=${month}`);
        const preencherCard = (seletor, valor) => {
            const element = document.querySelector(seletor);
            if (element) element.textContent = valor;
        };

        preencherCard('.card-azul .valor', formatCurrency(dados.summary.total_balance));
        preencherCard('.card-verde .valor', formatCurrency(dados.summary.monthly_income));
        preencherCard('.card-vermelho .valor', formatCurrency(dados.summary.monthly_expenses));
        preencherCard('.card-roxo .valor', dados.summary.debt_summary);

        const subtitle = document.querySelector('.subtitulo-pagina strong');
        if (subtitle && dados.period) {
            subtitle.textContent = `${String(dados.period.month).padStart(2, '0')}/${dados.period.year}`;
        }

        const tabelaRecentes = document.querySelector('.ultimas-transacoes-lista');
        if (tabelaRecentes) {
            tabelaRecentes.innerHTML = dados.recent?.length
                ? dados.recent.map(transaction => `
                    <tr>
                        <td><div class="icone ${transaction.type === 'entrada' ? 'text-success' : 'text-danger'} rounded-2" style="width:36px;height:36px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.06)"><i class="bi ${transaction.type === 'entrada' ? 'bi-arrow-down' : 'bi-arrow-up'}"></i></div></td>
                        <td><div class="fw-semibold">${escapeHtml(transaction.description)}</div><div class="text-secondary small">${escapeHtml(transaction.category)}</div></td>
                        <td class="text-secondary small">${escapeHtml(transaction.date)}</td>
                        <td class="text-end ${transaction.type === 'entrada' ? 'tag-positiva' : 'tag-negativa'}">${transaction.type === 'entrada' ? '+' : '-'} ${formatCurrency(transaction.amount)}</td>
                    </tr>
                `).join('')
                : '<tr><td colspan="4" class="text-center text-secondary py-4">Nenhum lançamento no período.</td></tr>';
        }

        const coupleBalance = dados.couple_balance || { amount: 0, direction: 'settled' };
        const balanceMessage = document.getElementById('saldoEntreMensagem');
        const balanceValue = document.getElementById('saldoEntreValor');
        if (balanceMessage && balanceValue) {
            if (coupleBalance.direction === 'partner_owes_current') balanceMessage.textContent = 'Seu parceiro deve a você';
            else if (coupleBalance.direction === 'current_owes_partner') balanceMessage.textContent = 'Você deve ao seu parceiro';
            else balanceMessage.textContent = 'Nenhuma diferença pendente';
            balanceValue.textContent = formatCurrency(coupleBalance.amount);
        }

        const categoriesList = document.getElementById('categoriasDashboard');
        if (categoriesList) {
            const totalCategories = dados.categories.reduce((sum, category) => sum + Number(category.value || 0), 0);
            categoriesList.innerHTML = dados.categories.length
                ? dados.categories.map((category, index) => {
                    const percentage = totalCategories ? Math.round((category.value / totalCategories) * 100) : 0;
                    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#6B7280', '#EC4899'];
                    return `<li class="d-flex justify-content-between py-1"><span><span class="d-inline-block rounded-circle me-2" style="width:10px;height:10px;background:${colors[index % colors.length]}"></span>${escapeHtml(category.name)}</span><strong>${formatCurrency(category.value)} <span class="text-secondary">${percentage}%</span></strong></li>`;
                }).join('')
                : '<li class="text-secondary">Nenhuma saída registrada no período.</li>';
        }

        try {
            const partner = await apiRequest('/couple/partner');
            if (partner?.parceiro) {
                const avatar = document.getElementById('saldoAvatarParceiro');
                if (avatar) avatar.textContent = iniciaisDoNome(partner.parceiro.nome);
            }
        } catch (error) {
            console.warn('Vínculo não disponível no dashboard:', error);
        }

        if (typeof Chart !== 'undefined') renderizarGraficosDashboard(dados);
    } catch (error) {
        if (isAuthError(error)) logout();
        else showToast(handleApiError(error, 'Erro ao sincronizar o dashboard.'), 'danger');
    }
}


function renderizarGraficosDashboard(dados) {
    const ctxRosca = document.getElementById('graficoCategorias')?.getContext('2d');
    if (ctxRosca) {
        instanciaChartRosca?.destroy();
        instanciaChartRosca = null;
        if (dados.categories?.length) {
            instanciaChartRosca = new Chart(ctxRosca, {
                type: 'doughnut',
                data: {
                    labels: dados.categories.map(category => category.name),
                    datasets: [{
                        data: dados.categories.map(category => category.value),
                        backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A78BFA', '#6B7280']
                    }]
                },
                options: { cutout: '70%', plugins: { legend: { display: false } } }
            });
        }
    }

    const ctxLinha = document.getElementById('graficoFluxo')?.getContext('2d');
    if (ctxLinha) {
        instanciaChartLinha?.destroy();
        instanciaChartLinha = new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dados.chart_data?.labels || [],
                datasets: [
                    { label: 'Entradas', data: dados.chart_data?.income || [], borderColor: '#10B981', tension: 0.4 },
                    { label: 'Saídas', data: dados.chart_data?.expenses || [], borderColor: '#EF4444', tension: 0.4 }
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


window.atualizarNomeUsuario = function (nome) {
    document.querySelectorAll('#perfilNome, #gavetaNome, #userNome').forEach(element => {
        element.textContent = nome;
    });
    document.querySelectorAll('#perfilFoto, #userIniciais').forEach(element => {
        element.textContent = iniciaisDoNome(nome);
    });
};
