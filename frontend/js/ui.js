/* =====================================================
   ✅ UI - top bar, sidebar, sininho, gaveta, notificações
   ===================================================== */
let atualizaNotifTimer = null;

window.addEventListener('DOMContentLoaded', async () => {
    const user = await checkAuth();
    if (!user) return;
    preencherPerfilNaTopBar(user);
    ligarBotaoSidebar();
    ligarSininho();
    // Atualiza notificações a cada 10s
    await carregarNotificacoes();
    atualizaNotifTimer = setInterval(carregarNotificacoes, 10000);
});

// =========================
// SIDEBAR - abrir/fechar
// =========================
function ligarBotaoSidebar() {
    const btn = document.getElementById('btnMenu');
    const sidebar = document.getElementById('sidebar');
    if (!btn || !sidebar) return;
    btn.addEventListener('click', () => {
        sidebar.classList.toggle('fechada');
        sidebar.classList.toggle('aberta');
    });
}

// =========================
// PERFIL NA TOP BAR
// =========================
function preencherPerfilNaTopBar(user) {
    const inicial = iniciaisDoNome(user.name);
    if (document.getElementById('perfilFoto'))  document.getElementById('perfilFoto').textContent  = inicial;
    if (document.getElementById('perfilNome'))  document.getElementById('perfilNome').textContent  = user.name;
    if (document.getElementById('gavetaNome'))  document.getElementById('gavetaNome').textContent  = user.name;
    if (document.getElementById('gavetaEmail')) document.getElementById('gavetaEmail').textContent = user.email;
}

// Atualiza o nome do usuário na interface (chamado após salvar alterações no perfil)
window.atualizarNomeUsuario = function(novoNome) {
    const inicial = iniciaisDoNome(novoNome);
    if (document.getElementById('perfilFoto'))  document.getElementById('perfilFoto').textContent  = inicial;
    if (document.getElementById('perfilNome'))  document.getElementById('perfilNome').textContent  = novoNome;
    if (document.getElementById('gavetaNome'))  document.getElementById('gavetaNome').textContent  = novoNome;
};

// =========================
// SININHO + NOTIFICAÇÕES
// =========================
function ligarSininho() {
    const btn = document.getElementById('marcarTodasLidas');
    if (btn) btn.addEventListener('click', marcarTodasLidas);
}

async function carregarNotificacoes() {
    const lista = document.getElementById('listaNotif');
    const cont  = document.getElementById('contadorNotif');
    if (!lista) return;
    
    try {
        const res = await fetch(`${API_URL}/couple/notifications`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (!res.ok) return;
        const notificacoes = await res.json();
        
        // Contar não lidas
        const naoLidas = notificacoes.filter(n => !n.is_read).length;
        const temLidas = notificacoes.some(n => n.is_read);
        
        // Atualizar contador
        if (cont) {
            if (naoLidas > 0) {
                cont.textContent = naoLidas;
                cont.style.display = 'flex';
            } else {
                cont.style.display = 'none';
            }
        }
        
        // Cabeçalho melhorado
        lista.innerHTML = `
            <li class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <strong class="small" style="font-size:13px;">
                    <i class="fa-solid fa-bell me-1 text-primary"></i>
                    Notificações
                    ${naoLidas > 0 ? `<span class="badge bg-primary bg-opacity-10 text-primary ms-2" style="font-size:10px;">${naoLidas} nova${naoLidas > 1 ? 's' : ''}</span>` : ''}
                </strong>
                <div class="d-flex gap-1 align-items-center">
                    ${temLidas ? `<button onclick="limparNotificacoesLidas()" class="btn-limpar-lidas" title="Limpar notificações lidas">
                        <i class="fa-solid fa-broom me-1"></i>Limpar
                    </button>` : ''}
                    <button class="btn btn-link p-0 text-decoration-none small" id="marcarTodasLidas" style="font-size:11px;">Marcar todas</button>
                </div>
            </li>
        `;
        
        if (notificacoes.length === 0) {
            lista.innerHTML += `
                <li class="p-5 text-center">
                    <div class="text-muted mb-2" style="font-size:32px;opacity:.3;">
                        <i class="fa-regular fa-bell"></i>
                    </div>
                    <div class="text-secondary small">Nenhuma notificação</div>
                </li>
            `;
            return;
        }
        
        // Renderizar cada notificação
        notificacoes.forEach(notif => {
            const li = document.createElement('li');
            li.className = 'p-3 border-bottom notif-item' + (notif.is_read ? ' notif-lida' : '');
            
            // Definir ícone e cor por tipo
            let icone = 'fa-bell';
            let corBg = 'rgba(108,117,125,.1)';
            let corIcone = '#6c757d';
            
            if (notif.type === 'invite_income') {
                icone = 'fa-user-plus';
                corBg = 'rgba(13,148,136,.12)';
                corIcone = '#0d9488';
            } else if (notif.type === 'invite_accepted') {
                icone = 'fa-heart';
                corBg = 'rgba(16,185,129,.12)';
                corIcone = '#10b981';
            } else if (notif.type === 'invite_rejected') {
                icone = 'fa-circle-xmark';
                corBg = 'rgba(220,38,38,.1)';
                corIcone = '#dc2626';
            } else if (notif.type === 'disconnect') {
                icone = 'fa-link-slash';
                corBg = 'rgba(217,119,6,.12)';
                corIcone = '#d97706';
            }
            
            // ⚠️ CORREÇÃO AQUI: usar notif.related_id ao invés de notif.id
            let botoes = '';
            if (notif.type === 'invite_income' && !notif.is_read && notif.related_id) {
                botoes = `
                    <div class="d-flex gap-2 mt-2">
                        <button onclick="aceitarConvite(${notif.related_id})" class="btn btn-success btn-acao-notif">
                            <i class="fa-solid fa-check me-1"></i>Aceitar
                        </button>
                        <button onclick="recusarConvite(${notif.related_id})" class="btn btn-outline-secondary btn-acao-notif">
                            <i class="fa-solid fa-times me-1"></i>Recusar
                        </button>
                    </div>
                `;
            }
            
            li.innerHTML = `
                <div class="d-flex gap-3">
                    <div class="icone-notif" style="background:${corBg};color:${corIcone};">
                        <i class="fa-solid ${icone}"></i>
                    </div>
                    <div class="flex-grow-1" style="min-width:0;">
                        <div class="d-flex justify-content-between align-items-start gap-2">
                            <div class="small fw-bold" style="color:${notif.is_read ? '#6b7280' : '#1f2937'};font-size:13px;">${notif.title}</div>
                            <button onclick="apagarNotificacao(${notif.id})" class="btn-apagar-notif" title="Apagar notificação">
                                <i class="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                        <div class="small" style="color:#6b7280;line-height:1.4;margin-top:2px;">${notif.message}</div>
                        <div class="text-muted mt-1" style="font-size:10px;">
                            <i class="fa-regular fa-clock me-1"></i>${formatarDataNotif(notif.created_at)}
                        </div>
                        ${botoes}
                    </div>
                </div>
            `;
            lista.appendChild(li);
        });
        
        // Reativar evento do botão marcar todas
        const btnMarcar = document.getElementById('marcarTodasLidas');
        if (btnMarcar) btnMarcar.addEventListener('click', marcarTodasLidas);
        
    } catch(e) {
        console.error('Erro ao carregar notificações:', e);
    }
}

function formatarDataNotif(dataStr) {
    try {
        const data = new Date(dataStr);
        const agora = new Date();
        const diffMs = agora - data;
        const diffMin = Math.floor(diffMs / 60000);
        const diffHora = Math.floor(diffMs / 3600000);
        const diffDia = Math.floor(diffMs / 86400000);
        
        if (diffMin < 1) return 'Agora mesmo';
        if (diffMin < 60) return `Há ${diffMin} min`;
        if (diffHora < 24) return `Há ${diffHora}h`;
        if (diffDia < 7) return `Há ${diffDia} dias`;
        return data.toLocaleDateString('pt-BR');
    } catch(e) {
        return '';
    }
}

async function aceitarConvite(id) {
    if (!confirm('✅ Aceitar esse vínculo? Vocês estarão conectados!')) return;
    try {
        const r = await fetch(`${API_URL}/couple/invite/${id}/accept`, {
            method:'POST',
            headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
        });
        if (r.ok) {
            showToast('🎉 Vínculo aprovado! Vocês estão conectados!','success');
            setTimeout(() => location.reload(), 1200);
        } else {
            const d = await r.json();
            showToast(d.detail || 'Erro ao aceitar vínculo', 'danger');
        }
    } catch(e) {
        showToast('Erro de conexão', 'danger');
    }
}
window.aceitarConvite = aceitarConvite;

async function recusarConvite(id) {
    if (!confirm('❌ Recusar esse vínculo?')) return;
    try {
        await fetch(`${API_URL}/couple/invite/${id}/reject`, {
            method:'POST',
            headers:{Authorization:`Bearer ${localStorage.getItem('token')}`}
        });
        showToast('Convite recusado','warning');
        carregarNotificacoes();
    } catch(e) {
        showToast('Erro de conexão', 'danger');
    }
}
window.recusarConvite = recusarConvite;

async function marcarTodasLidas() {
    try {
        // Tenta marcar como lidas, mas se o endpoint não existir, só recarrega
        await fetch(`${API_URL}/couple/notifications/read-all`, {
            method: 'PUT',
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        carregarNotificacoes();
        showToast('Notificações atualizadas','success');
    } catch(e){
        carregarNotificacoes();
    }
}

async function apagarNotificacao(id) {
    if (!confirm('🗑️ Apagar esta notificação?')) return;
    try {
        await fetch(`${API_URL}/couple/notifications/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        showToast('Notificação apagada', 'info');
        carregarNotificacoes();
    } catch(e) {
        showToast('Erro ao apagar', 'danger');
    }
}
window.apagarNotificacao = apagarNotificacao;

async function limparNotificacoesLidas() {
    if (!confirm('🗑️ Apagar todas as notificações já lidas?')) return;
    try {
        const r = await fetch(`${API_URL}/couple/notifications/clear/read`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
        });
        const d = await r.json();
        showToast(d.mensagem || 'Notificações limpas', 'info');
        carregarNotificacoes();
    } catch(e) {
        showToast('Erro ao limpar', 'danger');
    }
}
window.limparNotificacoesLidas = limparNotificacoesLidas;