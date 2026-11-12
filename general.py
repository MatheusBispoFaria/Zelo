"""Gráficos exploratórios do estudo do Zelo, com recortes e incerteza explícitos."""
import base64
import io
import json
import logging
import textwrap
import zipfile

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

from shared import analytics as analysis
from shared.components import icon, format_int

logger = logging.getLogger(__name__)
GREEN, YELLOW, INK = '#105d57', '#efb947', '#192a25'
EXAMS = {
    'tempo-entre-data-do-agendamento-do-procedimento-e-data-da-vaga-do-procedimento-para-mamografia': 'Mamografia',
    'tempo-entre-data-do-agendamento-do-procedimento-e-data-da-vaga-do-procedimento-para-ressonancia-magnetica': 'Ressonância magnética',
    'tempo-entre-data-do-agendamento-do-procedimento-e-data-da-vaga-do-procedimento-para-tomografia': 'Tomografia',
    'tempo-medio-de-espera-para-exames-prioritarios': 'Exames prioritários',
}
MODALITIES = {'primeira_consulta': 'Primeira consulta', 'interconsulta': 'Interconsulta', 'subsequente': 'Consulta de retorno'}
QUARTERS = ['2024-T1', '2024-T2', '2024-T3', '2024-T4', '2025-T1']
DEFAULTS = {'confidence': .95, 'iqr': False, 'factor': 1.5, 'zeros': False, 'exam': next(iter(EXAMS)),
            'modality': 'primeira_consulta', 'quarter': '2025-T1', 'threshold': 20,
            'coverage': 80, 'classification': 'acesso'}
COMPARABLE_EXAMS = {key:label for key,label in EXAMS.items() if not key.endswith('exames-prioritarios')}
MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out']


def field(label, control):
    return html.Div([html.Label(label), control], className='control-field')


def choose(id_, options, value):
    if isinstance(options, dict):options = [{'label': label, 'value': key} for key, label in options.items()]
    return dcc.Dropdown(id=id_, options=options, value=value, clearable=False, className='zelo-select')


def info_button(target, label):
    return html.Button('i', className='info-button', title=label,
                       **{'aria-label':label, 'data-open-dialog':target})


def popout(id_, title, content, class_name=''):
    return html.Dialog([
        html.Div([html.H2(title, id=id_+'-title'),
                  html.Button('×', className='dialog-close', title='Fechar',
                              **{'aria-label':'Fechar '+title, 'data-close-dialog':id_})], className='dialog-header'),
        html.Div(content, className='dialog-body'),
    ], id=id_, className='zelo-dialog '+class_name, **{'aria-labelledby':id_+'-title'})


def layout():
    return html.Div([
        html.Div([
            html.Div([html.H1(['Os dados por trás ', html.Em('do cuidado.')]),
                      html.Span('Estudo de caso · São Paulo', className='description')], className='overview-heading'),
            html.Div([
                info_button('fontes', 'Sobre as análises, fontes e métodos'),
                html.Button('Filtros', className='button', **{'data-open-dialog':'analysis-filters'}),
                html.Button([icon('download', '#ffffff'), 'Baixar recortes'], id='analysis-download-button',
                            n_clicks=0, disabled=True, className='button button-primary'),
            ], className='overview-actions'),
        ], className='analysis-hero'),
        popout('analysis-filters', 'Filtros e recortes da análise', [
            html.Div([
                field('Nível dos intervalos de confiança', choose('analysis-confidence', {0.90:'90%', .95:'95%', .99:'99%'}, .95)),
                field('Tratamento de extremos', dcc.Checklist(id='analysis-iqr', options=[{'label':'Remover extremos por IQR', 'value':'on'}],
                                                             value=[], labelClassName='check-label')),
                field('Limites do IQR', choose('analysis-factor', {1.5:'1,5 × IQR', 3.0:'3 × IQR'}, 1.5)),
                field('Zeros no tempo de espera', dcc.Checklist(id='analysis-zeros', options=[{'label':'Incluir zeros publicados', 'value':'on'}],
                                                               value=[], labelClassName='check-label')),
            ], className='controls-grid'),
            html.P('IQR atua apenas nas cópias usadas nos gráficos. Extremos podem ser reais, especialmente na chuva. Os ICs descrevem a incerteza das estimativas, sem corrigir falhas de cobertura ou seleção.',
                   className='description analysis-hint'),
            html.Div([
                html.H3('Exames, períodos e recortes'),
                html.Div([
                    field('Exame · capital paulista', choose('analysis-exam', EXAMS, DEFAULTS['exam'])),
                    field('Modalidade de consulta', choose('analysis-modality', MODALITIES, 'primeira_consulta')),
                    field('Trimestre · faltas por unidade e modalidade', choose('analysis-quarter', QUARTERS, '2025-T1')),
                    field('Limiar exploratório de chuva · mm/dia', choose('analysis-threshold', [10,20,30,50,80], 20)),
                    field('Cobertura mínima diária da estação', choose('analysis-coverage', {50:'50%',80:'80%',90:'90%',100:'100%'}, 80)),
                    field('Manifestações · classificação', choose('analysis-classification', {'acesso':'Reclamações e solicitações','todas':'Todas as classificações'}, 'acesso')),
                ], className='controls-grid'),
            ], className='analysis-recortes'),
        ], 'analysis-controls'),
        dcc.Loading(html.Div(id='analysis-content', className='analysis-busy'), color=GREEN, type='circle', delay_show=150,
                    parent_className='analysis-loading-shell', style={'height':'100%'}),
        dcc.Store(id='analysis-export'), dcc.Download(id='analysis-download'),
        method_section(),
    ], className='general-page')


def figure(x_title='', y_title=''):
    chart = go.Figure()
    chart.update_layout(template='plotly_white', paper_bgcolor='white', plot_bgcolor='white', height=340,
                        font={'family':'Segoe UI, Arial, sans-serif','size':12,'color':INK},
                        margin={'l':52,'r':18,'t':14,'b':76}, separators=',.',
                        xaxis_title=x_title, yaxis_title=y_title, hoverlabel={'font_size':12},
                        legend={'orientation':'h','y':-0.24,'x':0,'font':{'size':10}},
                        colorway=[GREEN,YELLOW,'#7d9c89'], uniformtext={'minsize':12,'mode':'show'}, uirevision='zelo-analysis')
    chart.update_xaxes(showgrid=False, zeroline=False, tickfont={'size':12}, title_font={'size':12})
    chart.update_yaxes(gridcolor='#edf0e9', zeroline=False, tickfont={'size':12}, title_font={'size':12})
    return chart


def empty(chart, message):
    chart.add_annotation(text='<br>'.join(textwrap.wrap(message, 46)), x=.5, y=.5, xref='paper', yref='paper',
                         showarrow=False, font={'size':12,'color':'#53675f'})
    return chart


def band(chart, x, low, high, name):
    chart.add_trace(go.Scatter(x=list(x), y=list(low), mode='lines', line={'width':0}, hoverinfo='skip', showlegend=False))
    chart.add_trace(go.Scatter(x=list(x), y=list(high), mode='lines', line={'width':0}, fill='tonexty',
                              fillcolor='rgba(16,93,87,0.13)', hoverinfo='skip', name=name))


def add_regression(chart, df, x, y, confidence, temporal=False):
    points, info = analysis.regression(df[x], df[y], confidence, temporal)
    if info['disponivel']:
        band(chart, points['x'], points['ic_inferior'], points['ic_superior'], f'IC {confidence:.0%} da média ajustada')
        chart.add_trace(go.Scatter(x=points['x'].tolist(), y=points['ajuste'].tolist(), mode='lines',
                                  line={'color':GREEN,'width':2,'dash':'dash'}, name='Regressão linear'))
    return points, info


def model_text(info, unit):
    if not info['disponivel']:return info['motivo']
    lower, upper = info['ic_inclinacao']
    r2 = f"{info['r_quadrado']:.2f}" if info['r_quadrado'] is not None else 'indefinido'
    return (f"Ajuste exploratório: n={info['n']}; inclinação {info['inclinacao']:.2f} {unit}; "
            f"IC {info['nivel_confianca']:.0%} [{lower:.2f}; {upper:.2f}]; R²={r2}.").replace('.', ',').rstrip(',') + '.'


def card(number, title, question, chart, caption, audit, wide=False, context=''):
    details = [html.Li('Fontes: ' + '; '.join(audit.get('fontes', []))),
               html.Li('Bases originais preservadas. Somente recortes e agregações analíticos.'),
               html.Li(f"IQR: {'ativo' if audit.get('iqr_ativo') else 'desligado ou não aplicável'}; {audit.get('retiradas_iqr', 0)} observações retiradas neste recorte.")]
    if audit.get('invalidos_retirados'):details.append(html.Li(f"Valores fora da faixa válida retirados: {audit['invalidos_retirados']}."))
    if audit.get('zeros_retirados'):details.append(html.Li(f"Zeros publicados retirados da espera: {audit['zeros_retirados']}. A interpretação permanece pendente."))
    details.append(html.Li('O relatório do download contém todos os critérios, limites do IQR e a metodologia dos intervalos.'))
    short_titles = {1:'Espera por exames',2:'Faltas por unidade',3:'Faltas por tipo de consulta',
                    4:'Qual exame demora mais?',5:'Dificuldades de acesso',6:'Quando a chuva passa do limiar?'}
    full = go.Figure(chart)
    full.update_layout(height=None, autosize=True)
    compact = compact_figure(chart, number)
    content = [html.P(question, className='chart-question'), html.P(caption, className='chart-caption')]
    if number <= 6:
        content.append(dcc.Graph(id=f'general-chart-{number}-expanded', figure=full, responsive=True,
                                 config={'displaylogo':False,'locale':'pt-br'}, className='expanded-graph'))
    if number in (2,5):
        content.append(html.P('O quadro principal mostra os seis maiores valores. O gráfico ampliado mantém os 12 valores do ranking original.', className='description'))
    content.extend([html.H3('Fonte e tratamento'), html.Ul(details, className='chart-audit')])
    return html.Section([
        html.Div([html.Span(f'{number:02d}', className='chart-number'),
                  html.H2(short_titles.get(number, title)),
                  info_button(f'chart-information-{number}', f'Informações e ampliação do gráfico {number}')],
                 className='chart-title-row'),
        html.P(context, className='description chart-context') if context else None,
        html.Div(dcc.Graph(id=f'general-chart-{number}', figure=compact if number <= 6 else full,
            responsive=True, config={'displaylogo':False,'responsive':True,'locale':'pt-br',
                                    'modeBarButtonsToRemove':['lasso2d','select2d'],
                                    'toImageButtonOptions':{'format':'png','filename':f'zelo-analise-{number}','scale':2}},
            style={'height':'100%','minHeight':0}), className='compact-plot'),
        popout(f'chart-information-{number}', f'{number:02d} · {title}', content),
    ], className=f'chart-card chart-position-{number}')


def compact_figure(chart, number):
    """Ajusta a apresentação; os cálculos e os recortes exportados são os mesmos."""
    compact = go.Figure(chart)
    compact.update_layout(height=None, autosize=True, margin={'l':42,'r':12,'t':6,'b':40},
                          showlegend=number == 1,
                          legend={'orientation':'h','y':-.22,'x':0,'font':{'size':10}})
    if number == 1:
        compact.update_layout(margin={'l':44,'r':12,'t':8,'b':65})
        compact.update_xaxes(title_text='Ano')
        compact.update_yaxes(title_text='Dias')
    elif number in (2,5):
        for trace in compact.data:
            trace.x = list(trace.x)[-6:]
            trace.y = list(trace.y)[-6:]
            if trace.customdata is not None:trace.customdata = list(trace.customdata)[-6:]
        compact.update_layout(margin={'l':132,'r':12,'t':5,'b':34})
        compact.update_xaxes(title_text='Faltas (%)' if number == 2 else 'Registros', nticks=4)
        compact.update_yaxes(dtick=1)
    elif number in (3,4):
        compact.update_layout(margin={'l':112,'r':14,'t':7,'b':32})
        compact.update_yaxes(title_text=None, showgrid=False, automargin=True)
        compact.update_xaxes(title_text='Média de taxas (%)' if number == 3 else 'Dias', nticks=4,
                             showgrid=True, gridcolor='#edf0e9', rangemode='tozero')
    elif number == 6:
        compact.update_layout(margin={'l':45,'r':12,'t':18,'b':26})
        compact.update_xaxes(title_text=None, tickangle=0, type='category')
        compact.update_yaxes(title_text='Dias (%)', nticks=3, rangemode='tozero')
    return compact


def bar_chart(frame, name, value, title):
    chart = figure(title)
    if frame.empty:return empty(chart, 'Nenhum registro atende aos critérios escolhidos.')
    shown = frame.sort_values(value, ascending=False).head(12).iloc[::-1]
    aliases = {'CONSULTA/ATENDIMENTO/TRATAMENTO':'Consulta/tratamento',
               'ESTABELECIMENTO DE SAÚDE':'Unidade de saúde',
               'DIAGNÓSTICO POR ULTRA-SONOGRAFIA':'Ultrassonografia',
               'DIAGNÓSTICO POR ENDOSCOPIA':'Endoscopia'} if name == 'tema' else {}
    labels = [aliases.get(str(v), str(v).title() if len(str(v)) <= 23 else str(v)[:22].title()+'…') for v in shown[name]]
    chart.add_trace(go.Bar(x=shown[value].tolist(), y=labels, orientation='h', marker_color=GREEN,
                          customdata=shown[name].tolist(), name='Observado', textposition='outside',
                          texttemplate='%{x:.1f}%' if value == 'valor' else '%{x:,.0f}',
                          textfont={'size':12}, constraintext='none', cliponaxis=False,
                          hovertemplate='%{customdata}<br>%{x:,.2f}<extra></extra>'))
    chart.update_layout(margin={'l':145,'r':18,'t':10,'b':55}, showlegend=False)
    chart.update_xaxes(gridcolor='#edf0e9', showgrid=True, range=[0,float(shown[value].max())*1.28 or 1])
    chart.update_yaxes(showgrid=False, automargin=True)
    return chart


def build_dashboard(config):
    c = {**DEFAULTS, **config}
    confidence, enabled, factor = c['confidence'], c['iqr'], c['factor']
    cards, frames, report = [], {}, {'criterios':c, 'originais_alterados':False, 'graficos':{},
        'escopo':'Análise exploratória de bases públicas; sem observações de uso do Zelo ou efeitos causais medidos.'}

    # 1. Tempo de espera como contexto. Não substitui a medida de economia de tempo.
    wait, info = analysis.waiting(c['exam'], c['zeros'], enabled, factor)
    chart = figure('Ano de referência', 'Tempo médio publicado · dias')
    chart.add_trace(go.Scatter(x=wait['ano'].tolist(), y=wait['valor'].tolist(), mode='lines+markers',
                              marker={'color':YELLOW,'size':8,'line':{'color':GREEN,'width':1}}, line={'color':'#b3c6bb','width':1}, name='Espera publicada'))
    fit, model = add_regression(chart, wait, 'ano', 'valor', confidence, True)
    if wait.empty:empty(chart, 'Sem anos válidos neste recorte.')
    chart.update_xaxes(dtick=2, tickformat='d')
    interval = 'solicitação até realização' if c['exam'].endswith('exames-prioritarios') else 'agendamento até a vaga'
    info['regressao'] = model
    cards.append(card(1, 'Como evoluiu a espera por exames?',
        f"Quanto tempo o Zelo poderia ajudar a economizar? Contexto observado: {EXAMS[c['exam']]} na capital, intervalo de {interval}.",
        chart, 'Este histórico não mede tempo economizado pelo Zelo. A faixa representa a média ajustada do modelo, não um intervalo da taxa publicada ou previsão de atendimento. ' + model_text(model, 'dias/ano'), info, True,
        context=f"{EXAMS[c['exam']]} · capital paulista"))
    frames['01_espera_observada'] = wait
    frames['01_regressao_espera'] = fit
    report['graficos']['01_espera'] = info

    # 2. Ranking preservado: uma modalidade e um trimestre por vez.
    ranked, rates, info = analysis.absence(c['modality'], c['quarter'], enabled, factor)
    chart = bar_chart(ranked, 'unidade_nome', 'valor', 'Taxa de faltas publicada · %')
    cards.append(card(2, 'Onde as faltas merecem mais atenção?',
        f"Qual caso operacional é mais alarmante? Até 12 maiores taxas em {c['quarter']} · {MODALITIES[c['modality']]}.", chart,
        'Ranking do recorte ambulatorial SES-SP, após os filtros. Não representa urgência clínica nem a fila de uma UPA. Sem o número de agendamentos, não há IC das taxas de cada unidade.', info,
        context=f"{c['quarter']} · {MODALITIES[c['modality']]}"))
    frames['02_ranking_faltas'] = ranked
    frames['02_taxas_incluidas'] = rates
    report['graficos']['02_faltas'] = info

    # 3. Comparação direta entre modalidades, com uma coorte pareada por unidade.
    means, paired, info = analysis.absence_modalities(c['quarter'], MODALITIES, enabled, factor, confidence)
    chart = figure('Média simples das taxas de faltas · %')
    if means.empty:empty(chart, 'Não há unidades com as três modalidades válidas neste recorte.')
    else:
        shown = means.sort_values('media')
        labels = {'primeira_consulta':'Primeira consulta','interconsulta':'Interconsulta','subsequente':'Retorno'}
        errors = None
        if info['ic_disponivel']:
            errors = {'type':'data','symmetric':False,
                'array':(shown['ic_superior']-shown['media']).clip(lower=0).tolist(),
                'arrayminus':(shown['media']-shown['ic_inferior']).clip(lower=0).tolist(),
                'color':'#192a25','thickness':1.5,'width':4}
        chart.add_trace(go.Bar(x=shown['media'].tolist(), y=shown['modalidade'].map(labels).tolist(),
            orientation='h', marker_color=GREEN, error_x=errors, texttemplate='%{x:.1f}%', textposition='inside',
            insidetextanchor='middle', textfont={'size':12,'color':'white'}, constraintext='none', customdata=shown['unidades'].tolist(),
            hovertemplate='%{y}<br>Média de taxas: %{x:.2f}%<br>%{customdata} unidades na mesma coorte<extra></extra>'))
        maximum = max(float(shown['media'].max()), float(shown['ic_superior'].max()) if info['ic_disponivel'] else 0)
        chart.update_xaxes(range=[0,maximum*1.2 or 1])
        chart.update_yaxes(showgrid=False, automargin=True)
        chart.update_layout(showlegend=False, margin={'l':140,'r':20,'t':15,'b':50})
    cards.append(card(3, 'Em qual modalidade de consulta há mais faltas?',
        'Onde faria sentido testar lembretes de confirmação primeiro?', chart,
        'Compara as mesmas unidades nas três modalidades no trimestre escolhido. Barras mostram a média simples das taxas, não a taxa de pacientes da rede. As hastes mostram IC exploratório por bootstrap pareado de unidades. O gráfico não mede efeito do Zelo.', info,
        context=f"{c['quarter']} · mesmas {info['coorte_completa_unidades']} unidades · "+(f'IC {confidence:.0%}' if info['ic_disponivel'] else 'IC indisponível')))
    frames['03_modalidades_media_ic'] = means
    frames['03_unidades_pareadas'] = paired
    report['graficos']['03_modalidades'] = info

    # 4. Mesma definição de espera e mesmo ano, sem misturar exames prioritários.
    comparisons, info = analysis.waiting_comparison(COMPARABLE_EXAMS, c['zeros'], enabled, factor)
    chart = figure('Tempo publicado entre agendamento e vaga · dias')
    if comparisons.empty:empty(chart, 'Não há um ano comum aos três exames após os filtros.')
    else:
        shown = comparisons.sort_values('valor')
        names = shown['exame'].replace({'Ressonância magnética':'Ressonância'})
        chart.add_trace(go.Bar(x=shown['valor'].tolist(), y=names.tolist(), orientation='h', marker_color=GREEN,
            texttemplate='%{x:.0f} dias', textposition='outside', textfont={'size':12}, cliponaxis=False,
            hovertemplate='%{y}<br>%{x:.0f} dias entre agendamento e vaga<extra></extra>'))
        chart.update_xaxes(range=[0,float(shown['valor'].max())*1.3 or 1])
        chart.update_yaxes(showgrid=False, automargin=True)
        chart.update_layout(showlegend=False, margin={'l':140,'r':30,'t':15,'b':50})
    cards.append(card(4, 'Qual exame tem a maior espera no mesmo ano?',
        'Qual espera merece mais atenção no acompanhamento das consultas?', chart,
        'Último ano comum aos três exames após os filtros, no município de São Paulo. Compara apenas agendamento até a vaga. Exames prioritários ficam fora porque medem outro intervalo. Sem denominadores ou dispersão da fonte, não há IC dos valores publicados.', info,
        context=f"São Paulo · {info['ano_comum'] or 'sem ano comum'} · agendamento até vaga"))
    frames['04_comparacao_espera_mesmo_ano'] = comparisons
    report['graficos']['04_comparacao_espera'] = info

    # 5. Não eliminar manifestações iguais sem identificador único de evento.
    topics, info = analysis.complaints(c['classification'])
    chart = bar_chart(topics, 'tema', 'registros', 'Manifestações no recorte')
    cards.append(card(5, 'Quais dificuldades aparecem na ouvidoria?',
        'O que fundamenta investigar a necessidade de um assistente? Temas das manifestações ligadas a SP.', chart,
        f"{format_int(info['registros_no_recorte'])} registros na seleção, considerando origem SP OU destino SP. Exibe até 12 temas. São manifestações publicadas, não prevalência entre cidadãos. Linhas iguais foram mantidas: não há ID que comprove duplicação do evento.", info,
        context='2025 · manifestações com origem ou destino em SP'))
    frames['05_temas_ouvidoria'] = topics
    report['graficos']['05_ouvidoria'] = info

    # 6. Comparação mensal; não confundir observações de chuva com alagamentos.
    stations, daily, info = analysis.rain(c['threshold'], c['coverage'], enabled, factor)
    monthly = analysis.rain_monthly(daily)
    chart = figure('Mês de 2026', 'Dias-estação acima do limiar · %')
    if daily.empty:empty(chart, 'Nenhuma estação tem a cobertura mínima escolhida.')
    else:
        values = monthly['percentual_dias']
        chart.add_trace(go.Bar(x=MONTHS, y=values.tolist(),
            marker_color=[YELLOW if pd.notna(v) and v==values.max() else GREEN for v in values],
            text=[f'{v:.1f}%'.replace('.',',') if pd.notna(v) else '' for v in values],
            textposition='outside', textfont={'size':12}, cliponaxis=False,
            customdata=monthly[['dias_acima','dias_estacao','estacoes']].to_numpy().tolist(),
            hovertemplate='%{x}/2026<br>%{y:.1f}% das medições diárias completas acima do limiar<br>%{customdata[0]} acima / %{customdata[1]} dias-estação<br>%{customdata[2]} estações com dados neste mês<extra></extra>'))
        chart.update_yaxes(range=[0,float(values.max())*1.3 or 1])
    chart.update_layout(showlegend=False, margin={'l':60,'r':20,'t':20,'b':45})
    info['agregacao_mensal'] = 'Dias-estação acima do limiar / dias-estação completos incluídos em cada mês. Meses sem dados ficam indisponíveis, não zero.'
    cards.append(card(6, 'Em quais meses houve mais dias de chuva acima do limiar?',
        'Em qual parte do período observado vale investigar a demanda por avisos de chuva?', chart,
        f"Janeiro–outubro de 2026; limiar exploratório {c['threshold']} mm/dia UTC e cobertura mínima {c['coverage']}%. Cada estação em cada dia completo é uma observação. A cobertura e o número de estações variam entre meses; os denominadores estão no hover e no CSV. Isso descreve a janela observada, sem inferir sazonalidade anual, frequência de enchentes ou desempenho de alertas. Sem IC binomial que suponha independência dos dias.", info,
        context=f"Jan–out/2026 · {len(stations)} estações de SP · medições diárias completas ≥ {c['threshold']} mm"))
    frames['06_chuva_por_mes'] = monthly
    frames['06_dias_completos_incluidos'] = daily
    frames['06_cobertura_estacoes'] = stations
    report['graficos']['06_chuva'] = info

    last = wait.iloc[-1] if not wait.empty else None
    stats = html.Div([
        stat('Última espera incluída · capital', f"{last['valor']:.0f} dias" if last is not None else 'Sem recorte',
             f"{EXAMS[c['exam']]} · {int(last['ano'])}" if last is not None else 'Reveja os filtros'),
        stat('Filtros da análise', f'{factor:g}'.replace('.', ',')+' × IQR' if enabled else 'IQR desligado',
             'Exclusões apenas nos gráficos; limites no relatório'),
        stat('Incerteza das estimativas', f'IC {confidence:.0%}', 'Regressão da espera e comparação entre modalidades; hipóteses no método'),
    ], className='analysis-stats')
    gaps = html.Div([
        html.H3('O que ainda precisamos medir para testar o Zelo?'),
        html.P('Tempo economizado: tarefas equivalentes com e sem assistente, conclusão e erros. Não há observações de uso do Zelo nestas bases.'),
        html.P('Redução de faltas e reaproveitamento: agendamentos, presença, cancelamentos, reoferta e comparador. As séries públicas são uma referência de contexto.'),
        html.P('Avisos de enchente: ocorrências locais e horários dos avisos para medir acertos, falsos avisos e antecedência. Chuva sozinha não fornece esse resultado.'),
        html.P('Fila da UPA: eventos de chegada, triagem e atendimento. O cadastro hospitalar não substitui esses registros.'),
    ], className='hypothesis-gap')
    return [stats, html.Div(cards, className='chart-grid overview-grid'),
            popout('analysis-limitations', 'Limites e próximos passos do estudo', [gaps])], package(frames, report)


def stat(label, value, note):
    return html.Div([html.Span(label, className='stat-label'), html.Strong(value, className='stat-value'),
                     html.P(note, className='description')], className='panel stat-card')


def package(frames, report):
    sources = sorted({filename for info in report['graficos'].values() for filename in info.get('fontes', [])})
    report['integridade_fontes'] = {e['artifact']:e['artifact_sha256'] for e in analysis.catalog()['files'] if e['artifact'] in sources}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('relatorio_tratamento.json', json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        for name, frame in frames.items():
            archive.writestr(name+'.csv', frame.to_csv(index=False).encode('utf-8-sig'))
        archive.writestr('LEIA-ME.txt',
            'Recortes derivados exclusivamente para os gráficos do Zelo. Bases originais preservadas.\n'
            'Consulte relatorio_tratamento.json para fontes, filtros, exclusões, IQR, modelos e limites dos ICs.\n'
            'CSV: UTF-8 com BOM, separador vírgula e ponto decimal.\n'
            'Os ICs das regressões são da média ajustada, não intervalos de predição ou garantias individuais.\n'
            'Não há medições de uso do Zelo ou efeito causal do assistente.\n')
    return {'content':base64.b64encode(buffer.getvalue()).decode('ascii'), 'filename':'zelo-recortes-graficos.zip',
            'type':'application/zip', 'base64':True}


def method_section():
    links = {
        'SES-SP':'https://portaldatransparencia.saude.sp.gov.br/indicadores.php',
        'ObservaSampa':'https://dados-abertos-observasampa.prefeitura.sp.gov.br/saude',
        'Ministério da Saúde':'https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos',
        'OuvidorSUS':'https://dadosabertos.saude.gov.br/dataset/ouvidorsus',
        'INMET':'https://portal.inmet.gov.br/dadoshistoricos',
        'SP Águas':'https://dadosabertos.sp.gov.br/',
    }
    return popout('fontes', 'Fontes, critérios e limites', [
        html.P('As tabelas de Saúde e Enchentes continuam apresentando as bases originais. Conversões numéricas, exclusões de valores inválidos, junções e filtro IQR acontecem somente nas cópias analíticas.'),
        html.P('A regressão temporal de espera usa erros robustos HAC com uma defasagem. A faixa é um IC pontual da média ajustada dentro dos dados observados. A validade depende das hipóteses do modelo; não é previsão individual, correção de viés ou efeito do assistente.', className='description'),
        html.P('A comparação de modalidades usa as mesmas unidades em um trimestre e bootstrap pareado por unidade. O IC é exploratório e não representa uma taxa ponderada de toda a rede SUS. Rankings de taxas, médias anuais publicadas sem dispersão e contagens do acervo não recebem margens artificiais.', className='description'),
        html.P('IQR: limites Q1 − k×(Q3−Q1) e Q3 + k×(Q3−Q1). Grupos com menos de quatro valores ou IQR zero são mantidos. Ao ativar o filtro, o IC passa a descrever o recorte filtrado. Não é ajustado para incerteza da seleção de extremos.', className='description'),
        html.Div([html.A(label, href=url, target='_blank', rel='noopener noreferrer') for label, url in links.items()], className='method-links'),
        html.P('As análises descrevem o contexto das perguntas. Os efeitos do assistente ainda dependem de avaliação própria.', className='description'),
        html.Button('Limites e próximos passos', className='button', **{'data-open-dialog':'analysis-limitations'}),
    ])


def register_callbacks(app):
    @app.callback(Output('analysis-content','children'), Output('analysis-export','data'),
                  Output('analysis-download-button','disabled'),
                  Input('analysis-confidence','value'), Input('analysis-iqr','value'), Input('analysis-factor','value'),
                  Input('analysis-zeros','value'), Input('analysis-exam','value'), Input('analysis-modality','value'),
                  Input('analysis-quarter','value'), Input('analysis-threshold','value'), Input('analysis-coverage','value'),
                  Input('analysis-classification','value'))
    def update(confidence, iqr, factor, zeros, exam, modality, quarter, threshold, coverage, classification):
        config = {'confidence':confidence if confidence in (.90,.95,.99) else .95,
                  'iqr':'on' in (iqr or []), 'factor':factor if factor in (1.5,3.0) else 1.5,
                  'zeros':'on' in (zeros or []), 'exam':exam if exam in EXAMS else DEFAULTS['exam'],
                  'modality':modality if modality in MODALITIES else 'primeira_consulta',
                  'quarter':quarter if quarter in QUARTERS else '2025-T1',
                  'threshold':threshold if threshold in (10,20,30,50,80) else 20,
                  'coverage':coverage if coverage in (50,80,90,100) else 80,
                  'classification':classification if classification in ('acesso','todas') else 'acesso'}
        try:
            content, export = build_dashboard(config)
            return content, export, False
        except (OSError, ValueError, KeyError):
            logger.exception('Não foi possível construir os gráficos do Zelo')
            return html.Div([html.H2('Não foi possível preparar esta análise'),
                             html.P('Confira os arquivos e o manifesto na pasta data. As bases originais continuam preservadas.')],
                            className='error-note', role='alert'), None, True

    @app.callback(Output('analysis-download','data'), Input('analysis-download-button','n_clicks'),
                  State('analysis-export','data'), prevent_initial_call=True)
    def download(clicks, payload):
        return payload if clicks and payload else no_update
