"""Experiência demonstrativa de alerta e deslocamento, com cenário fictício."""
import json
from dash import dcc,html
from shared.components import icon
from shared.simulation import ORIGINS,SCENARIOS,simulate_route


def layout():
    initial = simulate_route(active=False)
    return html.Div([
        html.Div([
            html.Div([html.H1(['Zelo avisa. ',html.Em('Você se orienta.')]),
                      html.P('Demonstração: localização, alagamentos, vias da rede e abrigos fictícios.',className='description')]),
            html.Button('i',className='info-button',title='Sobre a simulação',
                        **{'aria-label':'Sobre a simulação','data-open-dialog':'simulator-information'}),
        ],className='simulator-heading'),
        html.Div([
            html.Aside([
                html.H2('Um aviso muda o caminho.'),
                html.Label('Localização hipotética',htmlFor='sim-origin'),
                html.Select([html.Option(label,value=key) for key,(_,label) in ORIGINS.items()],id='sim-origin',className='sim-select'),
                html.Label('Cenário de alagamento',htmlFor='sim-scenario'),
                html.Select([html.Option(label,value=key) for key,label in SCENARIOS.items()],id='sim-scenario',className='sim-select'),
                html.Div([
                    html.Button([icon('alert','#fff'),'Simular alerta'],id='sim-start',className='button button-primary',**{'data-sim-action':'start'}),
                    html.Button('Reiniciar',className='button',**{'data-sim-action':'reset'}),
                ],className='sim-actions'),
                dcc.Checklist(id='sim-sound',options=[{'label':'Som demonstrativo','value':'on'}],value=['on'],labelClassName='sim-sound-option'),
                html.P('Som ao simular. Vibração física depende do aparelho.',className='description',id='sim-audio-status'),
                html.Section([
                    html.Div([html.Span(className='sim-status-dot'),html.H3('Pronto para simular',id='sim-status-title')],className='sim-result-title'),
                    html.P('Sua posição aparece em azul no mapa.',id='sim-route-description'),
                    html.Div([
                        html.Div([html.Span('Trajeto no cenário',className='description'),html.Strong('—',id='sim-distance')]),
                        html.Div([html.Span('Trechos bloqueados',className='description'),html.Strong('—',id='sim-blocked')]),
                    ],className='sim-metrics'),
                ],className='sim-result',**{'aria-live':'polite'}),
                html.Button('Repetir aviso',id='sim-repeat',className='button sim-repeat',disabled=True,**{'data-sim-action':'replay'}),
                html.P('Rota demonstrativa. Não use este cenário para uma evacuação real.',className='description sim-footnote'),
            ],className='sim-controls'),
            html.Section([
                html.Div(id='simulator-map',className='sim-map',role='region',**{'aria-label':'Mapa interativo da demonstração de enchente'}),
                html.Div([html.Strong('SIMULAÇÃO · ALERTA DE ALAGAMENTO'),
                          html.Span('Possível alagamento no cenário. O Zelo está calculando um trajeto com menor exposição.',id='sim-alert-text')],
                         className='sim-alert-banner',id='sim-alert',role='alert',hidden=True),
                html.Div([
                    html.Span([html.I(className='legend-dot user'),'Você (simulado)']),
                    html.Span([html.I(className='legend-dot risk'),'Área simulada']),
                    html.Span([html.I(className='legend-dot route'),'Rota sugerida']),
                ],className='sim-map-legend'),
                html.Div([
                    html.Div(className='phone-island'),
                    html.Div([html.Span('Z',className='phone-brand'),html.Div([html.Strong('Zelo'),html.Span('Seu assistente',className='description')])],className='phone-header'),
                    html.Div([
                        html.Span('DEMONSTRAÇÃO',className='phone-demo-tag'),
                        html.Div('Seu dia, com mais cuidado.',id='sim-phone-title',className='phone-message-title'),
                        html.P('O próximo aviso aparece aqui quando você iniciar a simulação.',id='sim-phone-message'),
                        html.Div([html.Span('↗'),html.P('Seu caminho será exibido no mapa.',id='sim-phone-route')],className='phone-route'),
                        html.Span('Vibração representada na animação',className='description phone-vibration-note'),
                    ],className='phone-screen'),
                    html.Div(className='phone-home-indicator'),
                    html.Span(')))',className='phone-sound-wave',**{'aria-hidden':'true'}),
                ],className='sim-phone',id='sim-phone',role='img',**{'aria-label':'Celular demonstrativo do Zelo, com animação de vibração ao receber um aviso'}),
                html.Span('Mapa de fundo: OpenStreetMap. A rede e os eventos sobrepostos são fictícios.',className='sim-map-note'),
            ],className='sim-map-stage'),
        ],className='simulator-workspace'),
        html.Dialog([
            html.Div([html.H2('Como funciona esta demonstração'),html.Button('×',className='dialog-close',
                      **{'aria-label':'Fechar informações da simulação','data-close-dialog':'simulator-information'})],className='dialog-header'),
            html.Div([
                html.P('Este simulador demonstra a experiência de um aviso, a animação e a escolha de uma rota em uma rede fictícia sobre um mapa de fundo. Não solicita sua geolocalização.'),
                html.P('As bases de precipitação do projeto são observações históricas. As áreas de alagamento e os abrigos deste cenário foram criados para a demonstração; não são previsões nem locais operacionais confirmados.'),
                html.P('Dijkstra elimina trechos bloqueados e minimiza distância × (1 + 8 × risco relativo). A rota só é uma solução dentro dessas premissas. Quando a origem fica isolada, o sistema informa que não há caminho disponível.'),
                html.P('O áudio é breve e começa após o clique. A vibração física depende do navegador e do aparelho; a animação funciona também no computador. O botão Reiniciar interrompe os efeitos.'),
                html.P('O mapa de fundo usa OpenStreetMap quando há conexão. A rede demonstrativa continua visível se os blocos do mapa não carregarem.',className='description'),
            ],className='dialog-body'),
        ],id='simulator-information',className='zelo-dialog',**{'aria-label':'Como funciona esta demonstração'}),
    ],id='simulator-root',className='simulator-page',**{'data-initial-scene':json.dumps(initial,ensure_ascii=False)})
