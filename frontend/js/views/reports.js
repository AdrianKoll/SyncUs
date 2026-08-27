const {
    apiRequest,
    downloadTextFile,
    escapeHtml,
    formatCurrency,
    formatDate,
    formatarPagador,
    handleApiError,
    showToast,
} = window;

let relatorioDados = null;
let relatorioTransacoes = [];
let relatorioCharts = [];

async function inicializarRelatorios() {
    const periodo = document.getElementById('relatorioPeriodo');
    if (!periodo) return;
    if (!periodo.dataset.bound) {
        periodo.value = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`;
        periodo.addEventListener('change', carregarRelatorioDados);
        document.getElementById('filtroQuem')?.addEventListener('change', carregarRelatorioDados);
        document.getElementById('gerarRelatorioBtn')?.addEventListener('click', gerarRelatorio);
        periodo.dataset.bound = 'true';
    }
    await carregarRelatorioDados();
}

async function carregarRelatorioDados() {
    const periodoElement = document.getElementById('relatorioPeriodo');
    if (!periodoElement) return;
    const tokenDaView = window.__syncusViewToken;
    const [year, month] = periodoElement.value.split('-').map(Number);
    try {
        const payer = document.getElementById('filtroQuem')?.value || 'ambos';
        relatorioDados = await apiRequest(
            `/transactions/report?year=${year}&month=${month}&payer=${encodeURIComponent(payer)}`
        );
        relatorioTransacoes = relatorioDados.transactions || [];
        if (tokenDaView !== window.__syncusViewToken || !document.getElementById('relatorioPeriodo')) return;
        renderizarRelatorio();
    } catch (error) {
        if (tokenDaView !== window.__syncusViewToken) return;
        showToast(handleApiError(error, 'Não foi possível carregar o relatório.'), 'danger');
    }
}

function renderizarRelatorio() {
    if (!relatorioDados) return;
    const periodoElement = document.getElementById('relatorioPeriodo');
    const formatoElement = document.getElementById('formatoRelatorio');
    if (!periodoElement || !formatoElement) return;

    const summary = relatorioDados.summary;
    const aggregates = relatorioDados.aggregates || {};
    const payerTotals = aggregates.payer_totals || { eu: '0.00', parceira: '0.00', ambos: '0.00' };
    const categories = aggregates.categories || [];
    const daily = aggregates.daily || {};
    const saldoElement = document.getElementById('relatorioSaldo');
    const entradasElement = document.getElementById('relatorioEntradas');
    const saidasElement = document.getElementById('relatorioSaidas');
    const quantidadeElement = document.getElementById('relatorioQuantidade');
    const resumoElement = document.getElementById('resumoRelatorio');
    if (![saldoElement, entradasElement, saidasElement, quantidadeElement, resumoElement].every(Boolean)) return;

    saldoElement.textContent = formatCurrency(summary.total_balance);
    entradasElement.textContent = formatCurrency(summary.monthly_income);
    saidasElement.textContent = formatCurrency(summary.monthly_expenses);
    quantidadeElement.textContent = aggregates.transaction_count ?? relatorioTransacoes.length;

    relatorioCharts.forEach(chart => chart.destroy());
    relatorioCharts = [];
    if (window.Chart) {
        const grafCatElement = document.getElementById('grafCatRel');
        const grafMesElement = document.getElementById('grafMesRel');
        const grafQuemElement = document.getElementById('grafQuemRel');
        if (![grafCatElement, grafMesElement, grafQuemElement].every(Boolean)) return;

        relatorioCharts.push(new window.Chart(grafCatElement, {
            type: 'doughnut',
            data: {
                labels: categories.map(item => item.name),
                datasets: [{
                    data: categories.map(item => Number(item.value || 0)),
                    backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#6B7280', '#EC4899'],
                    borderWidth: 0,
                }],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
        }));

        const dailyEntries = Object.entries(daily);
        relatorioCharts.push(new window.Chart(grafMesElement, {
            type: 'bar',
            data: {
                labels: dailyEntries.map(([day]) => formatDate(day)),
                datasets: [
                    {
                        label: 'Entradas',
                        data: dailyEntries.map(([, values]) => Number(values.entrada || 0)),
                        backgroundColor: '#10B981',
                        borderRadius: 6,
                    },
                    {
                        label: 'Saídas',
                        data: dailyEntries.map(([, values]) => Number(values.saida || 0)),
                        backgroundColor: '#EF4444',
                        borderRadius: 6,
                    },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
        }));

        relatorioCharts.push(new window.Chart(grafQuemElement, {
            type: 'bar',
            data: {
                labels: ['Você', 'Parceiro(a)', 'Ambos'],
                datasets: [{
                    label: 'Gastos R$',
                    data: [Number(payerTotals.eu || 0), Number(payerTotals.parceira || 0), Number(payerTotals.ambos || 0)],
                    backgroundColor: ['#3B82F6', '#EC4899', '#8B5CF6'],
                    borderRadius: 10,
                }],
            },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
        }));
    }

    const maiorCategoria = categories[0];
    resumoElement.innerHTML = `<li class="py-1 border-bottom"><i class="bi bi-check-circle text-success me-2"></i>Saldo do período: <strong>${formatCurrency(summary.total_balance)}</strong></li><li class="py-1 border-bottom"><i class="bi bi-arrow-up text-danger me-2"></i>Saídas registradas: <strong>${formatCurrency(summary.monthly_expenses)}</strong></li><li class="py-1 border-bottom"><i class="bi bi-folder text-primary me-2"></i>Maior categoria: <strong>${maiorCategoria ? `${escapeHtml(maiorCategoria.name)} (${formatCurrency(maiorCategoria.value)})` : 'Nenhuma'}</strong></li><li class="py-1"><i class="bi bi-list-ul text-info me-2"></i>Total de registros: <strong>${aggregates.transaction_count ?? relatorioTransacoes.length}</strong></li>`;
}

function gerarRelatorio() {
    const formatoElement = document.getElementById('formatoRelatorio');
    const periodoElement = document.getElementById('relatorioPeriodo');
    if (!relatorioDados || !formatoElement || !periodoElement) {
        return showToast('Aguarde o carregamento dos dados.', 'warning');
    }

    const formato = formatoElement.value;
    const summary = relatorioDados.summary;
    const payload = {
        periodo: relatorioDados.period,
        resumo: summary,
        agregacoes: relatorioDados.aggregates,
        transacoes: relatorioTransacoes,
        geradoEm: new Date().toISOString(),
    };
    const filenameBase = `syncus-relatorio-${periodoElement.value}`;
    if (formato === 'json') {
        downloadTextFile(`${filenameBase}.json`, JSON.stringify(payload, null, 2), 'application/json');
    } else if (formato === 'txt') {
        downloadTextFile(
            `${filenameBase}.txt`,
            `RELATÓRIO FINANCEIRO SYNCUS\nPeríodo: ${payload.periodo.month}/${payload.periodo.year}\nEntradas: ${formatCurrency(summary.monthly_income)}\nSaídas: ${formatCurrency(summary.monthly_expenses)}\nSaldo: ${formatCurrency(summary.total_balance)}\nTransações: ${relatorioTransacoes.length}\n`,
            'text/plain;charset=utf-8',
        );
    } else {
        const rows = [
            ['Data', 'Descrição', 'Categoria', 'Tipo', 'Pago por', 'Valor'],
            ...relatorioTransacoes.map(item => [
                formatDate(item.date),
                item.description,
                item.category?.name || 'Outros',
                item.type,
                formatarPagador(item),
                item.amount,
            ]),
        ];
        downloadTextFile(
            `${filenameBase}.csv`,
            '\ufeff' + rows.map(row => row.map(value => `"${String(value ?? '').replaceAll('"', '""')}"`).join(';')).join('\n'),
            'text/csv;charset=utf-8',
        );
    }
    showToast(`Relatório ${formato.toUpperCase()} gerado.`, 'success');
}

window.inicializarRelatorios = inicializarRelatorios;
document.addEventListener('viewCarregada', () => {
    if (window.location.hash.replace('#/', '') === 'reports') inicializarRelatorios();
});
