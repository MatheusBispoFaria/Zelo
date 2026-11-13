"""Gráficos exploratórios do estudo do Zelo, com recortes e incerteza explícitos."""
import base64
import io
import json
import logging
import math
import textwrap
import zipfile

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

from shared import analytics as analysis
from shared import flood_analysis as flood_analysis
from shared.components import icon, format_int

logger = logging.getLogger(__name__)
GREEN, YELLOW, INK = '#105d57', '#efb947', '#192a25'
# Plotly usa pixels; mesma escala de 12 pt / 10 pt definida no CSS (96 dpi).
FONT_NORMAL, FONT_DESCRIPTION = 12 * 96 / 72, 10 * 96 / 72
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
            'coverage': 80, 'classification': 'acesso',
            'flood_year':2026, 'flood_kind':'ambos', 'flood_month':'todos', 'flood_place':'todas',
            'flood_window':1, 'flood_lag':0, 'flood_radius':30, 'flood_deduplicate':False}
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
                field('Intervalos de confiança', choose('analysis-confidence', {'off':'Desativar IC', 0.90:'90%', .95:'95%', .99:'99%'}, .95)),
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
            html.Div([
                html.H3('Ocorrências e precipitação · gráficos 7 e 8'),
                html.Div([
                    field('Ano das ocorrências',choose('analysis-flood-year',{2026:'2026 · até setembro',2025:'2025',2024:'2024'},2026)),
                    field('Tipo de ocorrência',choose('analysis-flood-kind',flood_analysis.KINDS,'ambos')),
                    field('Mês das ocorrências',choose('analysis-flood-month',{'todos':'Todos os meses',**dict(enumerate(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'],1))},'todos')),
                    field('Subprefeitura',choose('analysis-flood-place',{'todas':'Todas as subprefeituras',**flood_analysis.subprefectures()},'todas')),
                    field('Acumulado de chuva · 2026',choose('analysis-flood-window',{1:'1 dia civil',3:'3 dias civis',7:'7 dias civis'},1)),
                    field('Fim da janela de chuva · 2026',choose('analysis-flood-lag',{0:'Mesmo dia da abertura',1:'Dia anterior à abertura',2:'2 dias antes da abertura'},0)),
                    field('Distância máxima até a estação · 2026',choose('analysis-flood-radius',{10:'10 km',20:'20 km',30:'30 km',50:'50 km'},30)),
                    field('Repetições na cópia analítica',dcc.Checklist(id='analysis-flood-deduplicate',options=[{'label':'Unificar atributos idênticos','value':'on'}],value=[],labelClassName='check-label')),
                ],className='controls-grid'),
                html.P('Em 2026, a chuva usa a estação elegível mais próxima, com a cobertura mínima definida acima. Em 2025, há totais municipais apenas em setembro/outubro. Em 2024, o ranking está disponível; não há precipitação correspondente nas bases atuais.',className='description analysis-hint'),
            ],className='analysis-recortes'),
        ], 'analysis-controls'),
        dcc.Loading(html.Div(id='analysis-content', className='analysis-busy'), color=GREEN, type='circle', delay_show=150,
                    parent_className='analysis-loading-shell'),
        dcc.Store(id='analysis-export'), dcc.Download(id='analysis-download'),
        method_section(),
    ], id='general-page', className='general-page')


def figure(x_title='', y_title=''):
    chart = go.Figure()
    chart.update_layout(template='plotly_white', paper_bgcolor='white', plot_bgcolor='white', height=340,
                        font={'family':'Segoe UI, Arial, sans-serif','size':FONT_NORMAL,'color':INK},
                        margin={'l':52,'r':18,'t':14,'b':76}, separators=',.',
                        xaxis_title=x_title, yaxis_title=y_title, hoverlabel={'font_size':FONT_NORMAL},
                        legend={'orientation':'h','y':-0.24,'x':0,'font':{'size':FONT_DESCRIPTION}},
                        colorway=[GREEN,YELLOW,'#7d9c89'], uniformtext={'minsize':FONT_DESCRIPTION,'mode':'show'}, uirevision='zelo-analysis')
    chart.update_xaxes(showgrid=False, zeroline=False, tickfont={'size':FONT_DESCRIPTION}, title_font={'size':FONT_DESCRIPTION})
    chart.update_yaxes(gridcolor='#edf0e9', gridwidth=1, zeroline=False, tickfont={'size':FONT_DESCRIPTION}, title_font={'size':FONT_DESCRIPTION})
    return chart


def empty(chart, message):
    chart.add_annotation(text='<br>'.join(textwrap.wrap(message, 46)), x=.5, y=.5, xref='paper', yref='paper',
                         showarrow=False, font={'size':FONT_DESCRIPTION,'color':'#53675f'})
    return chart


def band(chart, x, low, high, name):
    chart.add_trace(go.Scatter(x=list(x), y=list(low), mode='lines', line={'width':0}, hoverinfo='skip', showlegend=False))
    chart.add_trace(go.Scatter(x=list(x), y=list(high), mode='lines', line={'width':0}, fill='tonexty',
                              fillcolor='rgba(16,93,87,0.08)', hoverinfo='skip', name=name))


def add_regression(chart, df, x, y, confidence, temporal=False):
    points, info = analysis.regression(df[x], df[y], confidence, temporal)
    if info['disponivel']:
        if confidence is not None:
            band(chart, points['x'], points['ic_inferior'], points['ic_superior'], f'IC {confidence:.0%} da média ajustada')
        chart.add_trace(go.Scatter(x=points['x'].tolist(), y=points['ajuste'].tolist(), mode='lines',
                                  line={'color':GREEN,'width':2,'dash':'dash'}, name='Regressão linear'))
    return points, info


def model_text(info, unit):
    if not info['disponivel']:return info['motivo']
    r2 = f"{info['r_quadrado']:.2f}" if info['r_quadrado'] is not None else 'indefinido'
    interval = 'IC desativado'
    if info['ic_inclinacao'] is not None:
        lower, upper = info['ic_inclinacao']
        interval = f"IC {info['nivel_confianca']:.0%} [{lower:.2f}; {upper:.2f}]"
    return (f"Ajuste exploratório: n={info['n']}; inclinação {info['inclinacao']:.2f} {unit}; "
            f"{interval}; R²={r2}.").replace('.', ',').rstrip(',') + '.'


def card(number, title, question, chart, caption, audit, wide=False, context=''):
    details = [html.Li('Fontes: ' + '; '.join(audit.get('fontes', []))),
               html.Li('Bases originais preservadas. Somente recortes e agregações analíticos.'),
               html.Li(f"IQR: {'ativo' if audit.get('iqr_ativo') else 'desligado ou não aplicável'}; {audit.get('retiradas_iqr', 0)} observações retiradas neste recorte.")]
    if audit.get('invalidos_retirados'):details.append(html.Li(f"Valores fora da faixa válida retirados: {audit['invalidos_retirados']}."))
    if audit.get('zeros_retirados'):details.append(html.Li(f"Zeros publicados retirados da espera: {audit['zeros_retirados']}. A interpretação permanece pendente."))
    if audit.get('repeticoes_iguais_unificadas'):details.append(html.Li(f"Repetições de atributos unificadas somente nesta análise: {audit['repeticoes_iguais_unificadas']}."))
    if 'registros_associados' in audit:details.append(html.Li(f"Registros associados à chuva: {audit['registros_associados']}; sem associação válida: {audit['registros_sem_associacao']}. Motivos e linhas estão no download."))
    details.append(html.Li('O relatório do download contém todos os critérios, limites do IQR e a metodologia dos intervalos.'))
    short_titles = {1:'Espera por exames',2:'Faltas por unidade',3:'Faltas por consulta',
                    4:'Espera entre exames',5:'Dificuldades de acesso',6:'Chuva acima do limiar',
                    7:'Chuva e ocorrências',8:'Locais com mais casos'}
    full = focus_figure(chart, number)
    compact = compact_figure(chart, number)
    content = [html.P(question, className='chart-question'), html.P(caption, className='chart-caption')]
    if number in (2,5,8):
        content.append(html.P('O quadro principal mostra os quatro maiores valores. Expandir mostra os 12 valores do ranking original, com os nomes completos.', className='description'))
    content.extend([html.H3('Fonte e tratamento'), html.Ul(details, className='chart-audit')])
    section = html.Section([
        html.Div([html.Span(f'{number:02d}', className='chart-number'),
                  html.H2(short_titles.get(number, title)),
                  info_button(f'chart-information-{number}', f'Informações do gráfico {number}')],
                 className='chart-title-row'),
        html.Div([
            html.P(context, className='description chart-context'),
            html.Button('Expandir', className='button chart-expand-button',
                **{'aria-label':f'Expandir gráfico {number}', 'aria-expanded':'false',
                   'aria-controls':f'chart-focus-{number}', 'data-open-dialog':f'chart-focus-{number}',
                   'data-expand-card':str(number)}),
        ],className='chart-subtitle-row'),
        html.Div(dcc.Graph(id=f'general-chart-{number}', figure=compact,
            responsive=True, config={'displaylogo':False,'responsive':True,'locale':'pt-br',
                                    'scrollZoom':False, 'doubleClick':'reset',
                                    'modeBarButtonsToRemove':['zoom2d','pan2d','lasso2d','select2d','zoomIn2d','zoomOut2d','autoScale2d'],
                                    'toImageButtonOptions':{'format':'png','filename':f'zelo-analise-{number}','scale':2}},
            style={'height':'100%','minHeight':0}), className='compact-plot'),
    ], className=f'chart-card chart-position-{number}')
    initial_axes = {}
    for name in ('xaxis','yaxis'):
        axis = getattr(full.layout,name)
        initial_axes[name+'.autorange'] = axis.autorange if axis.autorange is not None else True
        if axis.range is not None:
            initial_axes[name+'.range'] = list(axis.range)
            initial_axes[name+'.autorange'] = False
    focus = html.Dialog([
        html.Div([
            html.H2(short_titles.get(number,title), id=f'chart-focus-{number}-title'),
            html.Div([
                info_button(f'chart-information-{number}', f'Informações do gráfico {number} ampliado'),
                html.Button('Restaurar enquadramento', className='button chart-reset-button',
                    **{'data-reset-chart':f'general-chart-{number}-focus',
                       'data-reset-layout':json.dumps(initial_axes)}),
                html.Button('Minimizar', className='button button-primary',
                    **{'aria-label':f'Minimizar gráfico {number}', 'data-close-dialog':f'chart-focus-{number}'}),
            ],className='chart-focus-actions'),
        ],className='dialog-header'),
        html.Div([
            html.P(context, className='description chart-focus-context'),
            dcc.Graph(id=f'general-chart-{number}-focus', figure=full, responsive=True,
                config={'displaylogo':False,'locale':'pt-br','scrollZoom':False,'doubleClick':'reset',
                        'modeBarButtonsToRemove':['lasso2d','select2d'],
                        'toImageButtonOptions':{'format':'png','filename':f'zelo-analise-{number}','scale':2}},
                className='chart-focus-graph'),
        ],className='dialog-body chart-focus-body'),
    ], id=f'chart-focus-{number}', className='zelo-dialog chart-focus-dialog',
       **{'aria-labelledby':f'chart-focus-{number}-title', 'data-focused-chart':str(number)})
    return section, [popout(f'chart-information-{number}', f'{number:02d} · {title}', content), focus]


def focus_figure(chart, number):
    """Versão completa e independente do enquadramento da prévia."""
    full = go.Figure(chart)
    full.update_layout(height=None, autosize=True, dragmode='zoom')
    if number in (2,5,8):
        for trace in full.data:
            if trace.customdata is not None:
                trace.y = ['<br>'.join(textwrap.wrap(str(name).title(), 34)) for name in trace.customdata]
        full.update_layout(margin={'l':220,'r':50,'t':20,'b':60})
        full.update_yaxes(dtick=1, automargin=True)
    return full


def compact_figure(chart, number):
    """Ajusta a apresentação; os cálculos e os recortes exportados são os mesmos."""
    compact = go.Figure(chart)
    compact.update_layout(height=None, autosize=True, margin={'l':42,'r':12,'t':6,'b':40},
                          showlegend=number == 1, dragmode=False,
                          legend={'orientation':'h','y':-.22,'x':0,'font':{'size':FONT_DESCRIPTION}})
    if number == 1:
        compact.update_layout(margin={'l':44,'r':12,'t':8,'b':65})
        compact.update_xaxes(title_text='Ano')
        compact.update_yaxes(title_text='Dias')
    elif number in (2,5,8):
        for trace in compact.data:
            trace.x = list(trace.x)[-4:]
            trace.y = list(trace.y)[-4:]
            if trace.customdata is not None:trace.customdata = list(trace.customdata)[-4:]
        compact.update_layout(margin={'l':132,'r':12,'t':5,'b':23})
        compact.update_xaxes(title_text=None, nticks=4)
        compact.update_yaxes(dtick=1)
    elif number in (3,4):
        compact.update_layout(margin={'l':112,'r':14,'t':7,'b':32})
        compact.update_yaxes(title_text=None, showgrid=False, automargin=True)
        compact.update_xaxes(title_text='Faltas (%)' if number == 3 else 'Dias', nticks=4,
                             showgrid=True, gridcolor='#edf0e9', rangemode='tozero')
    elif number == 6:
        compact.update_layout(margin={'l':45,'r':12,'t':18,'b':26})
        compact.update_xaxes(title_text=None, tickangle=0, type='category',tickmode='array',tickvals=MONTHS[::2])
        compact.update_yaxes(title_text='Dias (%)', nticks=3, rangemode='tozero')
        for trace in compact.data:
            if trace.type=='bar':trace.textposition='none'
    elif number == 7:
        compact.update_layout(margin={'l':45,'r':12,'t':12,'b':32},showlegend=False)
        compact.update_xaxes(title_text=None,nticks=4)
        compact.update_yaxes(title_text='Chuva · mm',nticks=3,rangemode='tozero')
        if compact.layout.yaxis.tickvals:
            ticks=list(compact.layout.yaxis.tickvals)
            compact.update_yaxes(tickvals=[ticks[0],ticks[len(ticks)//2],ticks[-1]])
        for trace in compact.data:
            if trace.type=='scatter' and trace.marker.sizeref:
                trace.marker.sizeref*=3
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
    chart.add_trace(go.Bar(x=shown[value].tolist(), y=labels, orientation='h', marker_color=GREEN, width=.52,
                          customdata=shown[name].tolist(), name='Observado', textposition='outside',
                          texttemplate='%{x:.1f}%' if value == 'valor' else '%{x:,.0f}',
                          textfont={'size':FONT_DESCRIPTION}, constraintext='none', cliponaxis=False,
                          hovertemplate='%{customdata}<br>%{x:,.2f}<extra></extra>'))
    chart.update_layout(margin={'l':145,'r':18,'t':10,'b':55}, showlegend=False)
    chart.update_xaxes(gridcolor='#edf0e9', showgrid=True, range=[0,float(shown[value].max())*1.28 or 1])
    chart.update_yaxes(showgrid=False, automargin=True)
    return chart


def absence_boxplot(paired, means, confidence, show_ci):
    """Distribuições das taxas individuais; o diamante separado mostra média e IC."""
    chart = figure('Taxa de faltas por unidade · %')
    if paired.empty:return empty(chart, 'Não há unidades com as três modalidades válidas neste recorte.')
    labels = {'primeira_consulta':'Primeira consulta', 'interconsulta':'Interconsulta', 'subsequente':'Retorno'}
    for key, label in labels.items():
        rows = paired.loc[paired['modalidade_consulta'].eq(key)]
        chart.add_trace(go.Box(x=rows['valor'].tolist(), y=[label]*len(rows), name=label,
            orientation='h', quartilemethod='linear', boxpoints='outliers', notched=False,
            boxmean=False, width=.48, fillcolor='rgba(16,93,87,.16)',
            line={'color':GREEN,'width':1.8}, marker={'color':GREEN,'size':5},
            text=rows['unidade_nome'].tolist(), showlegend=False))
    if show_ci:
        chart.add_trace(go.Scatter(x=means['media'].tolist(), y=means['modalidade'].map(labels).tolist(),
            mode='markers', name=f'Média e IC {confidence:.0%}',
            marker={'symbol':'diamond','size':9,'color':YELLOW,'line':{'color':'#795516','width':1}},
            error_x={'type':'data','symmetric':False,
                'array':(means['ic_superior']-means['media']).clip(lower=0).tolist(),
                'arrayminus':(means['media']-means['ic_inferior']).clip(lower=0).tolist(),
                'color':'#a57518','thickness':2,'width':4},
            customdata=means[['ic_inferior','ic_superior','unidades']].to_numpy().tolist(),
            hovertemplate='%{y}<br>Média: %{x:.2f}%<br>IC: %{customdata[0]:.2f}% a %{customdata[1]:.2f}%<br>%{customdata[2]} unidades<extra></extra>'))
    chart.update_layout(margin={'l':145,'r':20,'t':15,'b':85}, showlegend=show_ci, boxmode='overlay')
    chart.update_yaxes(categoryorder='array', categoryarray=list(labels.values()), autorange='reversed', showgrid=False)
    chart.update_xaxes(rangemode='tozero', range=[0,float(paired['valor'].max())*1.1 or 1],
                       showgrid=True, gridcolor='#edf0e9')
    return chart


def flood_relation_figure(frame, info):
    chart=figure('Data de abertura do registro','Chuva acumulada na janela · mm')
    if frame.empty:return empty(chart,info.get('motivo','Nenhuma ocorrência possui chuva válida neste recorte. Reveja cobertura, raio ou IQR.'))
    if info['resolucao']=='mensal_municipal':
        chart.add_trace(go.Bar(x=frame['periodo'].tolist(),y=frame['chuva_mm'].tolist(),width=.45,
            marker_color=GREEN,text=[f'{n} registros' for n in frame['registros']],textposition='outside',cliponaxis=False,
            customdata=frame[['registros','alagamentos','inundacoes']].to_numpy().tolist(),
            hovertemplate='%{x}<br>Chuva municipal: %{y:.2f} mm<br>%{customdata[0]} registros no recorte<br>%{customdata[1]} alagamentos · %{customdata[2]} inundações<extra></extra>'))
        chart.update_xaxes(title_text='Mês de 2025',type='category')
        chart.update_yaxes(title_text='Chuva mensal da capital · mm',range=[0,float(frame['chuva_mm'].max())*1.3 or 1])
        chart.update_layout(showlegend=False)
        return chart
    colors=[GREEN,YELLOW,'#5c7990','#9a6f48'];symbols=['circle','diamond','square','triangle-up']
    max_count=int(frame['registros'].max())
    for i,(code,part) in enumerate(frame.groupby('estacao',sort=True)):
        hover=part[['registros','alagamentos','inundacoes','distancia_max_km','locais']].astype(object).values.tolist()
        for data,(_,row) in zip(hover,part.iterrows()):
            data.extend([row['janela_inicio'].strftime('%d/%m/%Y'),row['janela_fim'].strftime('%d/%m/%Y'),row['pico_horario_mm']])
        chart.add_trace(go.Scatter(x=part['data_abertura'].dt.strftime('%Y-%m-%d').tolist(),y=part['chuva_mm'].tolist(),
            mode='markers',name=f"{code} · {part['nome_estacao'].iloc[0].title()}",
            marker={'size':part['registros'].tolist(),'sizemode':'area','sizeref':2*max_count/(40**2),'sizemin':5,
                    'color':colors[i%len(colors)],'symbol':symbols[i%len(symbols)],'opacity':.72,'line':{'color':'white','width':1}},
            customdata=hover,
            hovertemplate='%{x|%d/%m/%Y} · abertura<br>Chuva: %{y:.1f} mm<br>Maior acumulado em 1h na janela: %{customdata[7]:.1f} mm<br>%{customdata[0]} registros · %{customdata[1]} alagamentos · %{customdata[2]} inundações<br>Janela: %{customdata[5]} a %{customdata[6]}<br>Maior distância à estação: %{customdata[3]:.1f} km<br>%{customdata[4]}<extra>%{fullData.name}</extra>'))
    chart.update_layout(legend={'itemsizing':'constant'},margin={'l':65,'r':25,'t':20,'b':90})
    chart.update_xaxes(type='date',tickformat='%d/%m')
    maximum=max(1.,float(frame['chuva_mm'].max()))
    scale=10**math.floor(math.log10(maximum/4))
    step=next(value*scale for value in (1,2,5,10) if value*scale>=maximum/4)
    ticks=[i*step for i in range(math.ceil(maximum/step)+1)]
    # Margem visual para as bolhas centradas em zero; os ticks continuam não negativos.
    chart.update_yaxes(range=[-maximum*.12,max(maximum*1.16,ticks[-1])],tickmode='array',tickvals=ticks)
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
                              marker={'color':GREEN,'size':5,'line':{'color':'white','width':.6}}, line={'color':'#81978c','width':1.4}, name='Espera publicada'))
    fit, model = add_regression(chart, wait, 'ano', 'valor', confidence, True)
    if wait.empty:empty(chart, 'Sem anos válidos neste recorte.')
    chart.update_xaxes(dtick=2, tickformat='d')
    interval = 'solicitação até realização' if c['exam'].endswith('exames-prioritarios') else 'agendamento até a vaga'
    info['regressao'] = model
    cards.append(card(1, 'Como evoluiu a espera por exames?',
        f"Quanto tempo o Zelo poderia ajudar a economizar? Contexto observado: {EXAMS[c['exam']]} na capital, intervalo de {interval}.",
        chart, 'Este histórico não mede tempo economizado pelo Zelo. ' +
        ('A faixa representa a média ajustada do modelo, não um intervalo da taxa publicada ou previsão de atendimento. ' if confidence is not None else 'A regressão permanece visível, com os intervalos desativados. ') +
        model_text(model, 'dias/ano'), info, True,
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

    # 3. Dispersão das taxas entre as mesmas unidades, separada por modalidade.
    means, paired, info = analysis.absence_modalities(c['quarter'], MODALITIES, enabled, factor, confidence)
    chart = absence_boxplot(paired, means, confidence, info['ic_disponivel'])
    cards.append(card(3, 'Como as faltas se distribuem por tipo de consulta?',
        'Quais modalidades apresentam maior dispersão das taxas entre unidades?', chart,
        'Cada caixa representa as taxas das mesmas unidades no trimestre: linha central = mediana; caixa = Q1 a Q3; bigodes = valores até 1,5 IQR; pontos externos permanecem visíveis. Caixas e bigodes não são intervalos de confiança. ' +
        ('O diamante amarelo e suas hastes mostram separadamente a média e seu IC exploratório por bootstrap pareado. ' if info['ic_disponivel'] else 'O diamante da média com IC não é exibido neste recorte. ') +
        'A variação é entre unidades, sem medir o efeito do Zelo.', info,
        context=f"{c['quarter']} · {info['coorte_completa_unidades']} unid. · "+('IC desativado' if confidence is None else f'◆ IC {confidence:.0%}' if info['ic_disponivel'] else 'IC indisponível')))
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
        chart.add_trace(go.Bar(x=shown['valor'].tolist(), y=names.tolist(), orientation='h', marker_color=GREEN, width=.5,
            texttemplate='%{x:.0f} dias', textposition='outside', textfont={'size':FONT_DESCRIPTION}, cliponaxis=False,
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
        context='Manifestações · SP · 2025'))
    frames['05_temas_ouvidoria'] = topics
    report['graficos']['05_ouvidoria'] = info

    # 6. Comparação mensal; não confundir observações de chuva com alagamentos.
    stations, daily, info = analysis.rain(c['threshold'], c['coverage'], enabled, factor)
    monthly = analysis.rain_monthly(daily)
    chart = figure('Mês de 2026', 'Dias-estação acima do limiar · %')
    if daily.empty:empty(chart, 'Nenhuma estação tem a cobertura mínima escolhida.')
    else:
        values = monthly['percentual_dias']
        chart.add_trace(go.Bar(x=MONTHS, y=values.tolist(), width=.55,
            marker_color=[YELLOW if pd.notna(v) and v==values.max() else GREEN for v in values],
            text=[f'{v:.1f}%'.replace('.',',') if pd.notna(v) else '' for v in values],
            textposition='outside', textfont={'size':FONT_DESCRIPTION}, cliponaxis=False,
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

    # 7 e 8 compartilham a seleção de ocorrências; chuva indisponível não elimina casos do ranking.
    ranked,occurrences,occ_info=flood_analysis.records(c['flood_year'],c['flood_kind'],c['flood_place'],c['flood_month'],c['flood_deduplicate'])
    relation,derived,relation_info=flood_analysis.relationship(occurrences,c['flood_year'],c['flood_month'],
        c['coverage'],c['flood_radius'],c['flood_window'],c['flood_lag'],enabled,factor)
    relation_info['repeticoes_iguais_unificadas']=occ_info['repeticoes_iguais_unificadas']
    chart=flood_relation_figure(relation,relation_info)
    resolution=relation_info['resolucao']
    relation_context=(f"2026 · {relation_info.get('registros_associados',0)}/{len(occurrences)} registros · bolha = quantidade"
                      if resolution=='diaria_estacao_proxima' else 'Chuva municipal disponível: set–out/2025' if resolution=='mensal_municipal' else f"{c['flood_year']} · sem associação neste recorte")
    cards.append(card(7,'Como a chuva se relaciona às ocorrências no tempo?',
        'Em quais datas os registros coincidem com maior chuva medida na região?',chart,
        'Em 2026, cada bolha reúne registros da mesma data de abertura e da mesma estação próxima. A altura é o acumulado medido na janela escolhida; a área da bolha representa a quantidade de registros. O hover mostra tipos, locais, estação, distância e datas da janela. Só entram medições diárias completas, sem trocar de estação para preencher lacunas. A data de abertura é interpretada como data civil paulista; não informa o horário de início físico da inundação. Em 2025, são comparados apenas os dois totais mensais disponíveis da capital e as respectivas contagens. O volume de chuva oferece contexto meteorológico, sem medir profundidade, danos, severidade ou causalidade. Sem IC artificial sobre medições e contagens.',
        relation_info,context=relation_context))
    frames['07_chuva_ocorrencias']=relation
    frames.update(derived)
    report['graficos']['07_chuva_ocorrencias']=relation_info
    chart=bar_chart(ranked,'local','registros','Registros publicados no recorte')
    if occ_info['fora_cobertura_publicada']:
        chart=empty(figure('Registros publicados'),'Este mês está fora da cobertura de ocorrências, disponível até setembro de 2026.')
    cards.append(card(8,'Quais locais concentram mais registros?',
        'Quais subprefeituras têm mais alagamentos ou inundações no período e tipo selecionados?',chart,
        f"{len(occurrences)} registros no recorte. Agrupamento por código de subprefeitura; o filtro separa alagamentos e inundações. O ranking permanece completo mesmo quando a chuva está indisponível ou é retirada por IQR no gráfico central. Mais registros não equivalem a maior risco por habitante nem a eventos independentes. 2026 é parcial até setembro. Unificação de atributos idênticos é opcional e acontece somente nas cópias analíticas.",
        occ_info,context=f"{c['flood_year']} · {flood_analysis.KINDS[c['flood_kind']]} · {len(occurrences)} registros"))
    frames['08_ranking_subprefeituras']=ranked
    frames['08_ocorrencias_incluidas']=occurrences
    report['graficos']['08_locais']=occ_info

    last = wait.iloc[-1] if not wait.empty else None
    stats = html.Div([
        stat('Última espera incluída · capital', f"{last['valor']:.0f} dias" if last is not None else 'Sem recorte',
             f"{EXAMS[c['exam']]} · {int(last['ano'])}" if last is not None else 'Reveja os filtros'),
        stat('Filtros da análise', f'{factor:g}'.replace('.', ',')+' × IQR' if enabled else 'IQR desligado',
             'Exclusões apenas nos gráficos; limites no relatório'),
        stat('Incerteza das estimativas', 'IC desativado' if confidence is None else f'IC {confidence:.0%}',
             'Intervalos não calculados; distribuições preservadas' if confidence is None else 'Regressão da espera e comparação entre modalidades; hipóteses no método'),
    ], className='analysis-stats')
    gaps = html.Div([
        html.H3('O que ainda precisamos medir para testar o Zelo?'),
        html.P('Tempo economizado: tarefas equivalentes com e sem assistente, conclusão e erros. Não há observações de uso do Zelo nestas bases.'),
        html.P('Redução de faltas e reaproveitamento: agendamentos, presença, cancelamentos, reoferta e comparador. As séries públicas são uma referência de contexto.'),
        html.P('Avisos de enchente: ocorrências locais e horários dos avisos para medir acertos, falsos avisos e antecedência. Chuva sozinha não fornece esse resultado.'),
        html.P('Fila da UPA: eventos de chegada, triagem e atendimento. O cadastro hospitalar não substitui esses registros.'),
    ], className='hypothesis-gap')
    sections, dialogs = zip(*cards)
    return [stats, html.Div(list(sections), className='chart-grid overview-grid'),
            html.Div([dialog for group in dialogs for dialog in group], className='analysis-dialog-host'),
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
        'GeoSampa · Defesa Civil':'https://metadados.geosampa.prefeitura.sp.gov.br/geonetwork/srv/api/records/432c06b1-03a1-4b1f-9210-423e1b58e869',
    }
    return popout('fontes', 'Fontes, critérios e limites', [
        html.P('As tabelas de Saúde e Enchentes continuam apresentando as bases originais. Conversões numéricas, exclusões de valores inválidos, junções e filtro IQR acontecem somente nas cópias analíticas.'),
        html.P('A regressão temporal de espera usa erros robustos HAC com uma defasagem. A faixa é um IC pontual da média ajustada dentro dos dados observados. A validade depende das hipóteses do modelo; não é previsão individual, correção de viés ou efeito do assistente.', className='description'),
        html.P('A comparação de modalidades usa as mesmas unidades em um trimestre e bootstrap pareado por unidade. O IC é exploratório e não representa uma taxa ponderada de toda a rede SUS. Rankings de taxas, médias anuais publicadas sem dispersão e contagens do acervo não recebem margens artificiais.', className='description'),
        html.P('IQR: limites Q1 − k×(Q3−Q1) e Q3 + k×(Q3−Q1). Grupos com menos de quatro valores ou IQR zero são mantidos. Ao ativar o filtro, o IC passa a descrever o recorte filtrado. Não é ajustado para incerteza da seleção de extremos.', className='description'),
        html.P('Chuva e ocorrências: em 2026, cada registro é associado à estação elegível mais próxima dentro do raio, com cobertura mínima e janela de dias civis completos em São Paulo. A hipótese de data civil é explícita porque o registro não publica hora/fuso. A chuva horária do INMET é atribuída à hora anterior à mensagem UTC e convertida para America/Sao_Paulo. Lacunas não viram zeros, nem provocam troca diária de estação. IQR atua sobre dias-estação, antes de repetir o valor para registros. A bolha agrega data e estação, sem criar medições independentes por chamado. Em 2025, a chuva permanece municipal/mensal; em 2024, o gráfico central não inventa precipitação ausente.',className='description'),
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
                  Input('analysis-classification','value'),
                  Input('analysis-flood-year','value'),Input('analysis-flood-kind','value'),Input('analysis-flood-month','value'),
                  Input('analysis-flood-place','value'),Input('analysis-flood-window','value'),Input('analysis-flood-lag','value'),
                  Input('analysis-flood-radius','value'),Input('analysis-flood-deduplicate','value'))
    def update(confidence, iqr, factor, zeros, exam, modality, quarter, threshold, coverage, classification,
               flood_year,flood_kind,flood_month,flood_place,flood_window,flood_lag,flood_radius,flood_deduplicate):
        config = {'confidence':None if confidence == 'off' else confidence if confidence in (.90,.95,.99) else .95,
                  'iqr':'on' in (iqr or []), 'factor':factor if factor in (1.5,3.0) else 1.5,
                  'zeros':'on' in (zeros or []), 'exam':exam if exam in EXAMS else DEFAULTS['exam'],
                  'modality':modality if modality in MODALITIES else 'primeira_consulta',
                  'quarter':quarter if quarter in QUARTERS else '2025-T1',
                  'threshold':threshold if threshold in (10,20,30,50,80) else 20,
                  'coverage':coverage if coverage in (50,80,90,100) else 80,
                  'classification':classification if classification in ('acesso','todas') else 'acesso',
                  'flood_year':flood_year if flood_year in flood_analysis.LIMITS else 2026,
                  'flood_kind':flood_kind if flood_kind in flood_analysis.KINDS else 'ambos',
                  'flood_month':flood_month if flood_month in range(1,13) else 'todos',
                  'flood_place':flood_place if flood_place in flood_analysis.subprefectures() else 'todas',
                  'flood_window':flood_window if flood_window in (1,3,7) else 1,
                  'flood_lag':flood_lag if flood_lag in (0,1,2) else 0,
                  'flood_radius':flood_radius if flood_radius in (10,20,30,50) else 30,
                  'flood_deduplicate':'on' in (flood_deduplicate or [])}
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
