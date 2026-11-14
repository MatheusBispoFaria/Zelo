"""Experiência demonstrativa de alerta e deslocamento, com cenário fictício."""
import json
from dash import dcc,html
from shared.components import icon
from shared.simulation import DEFAULT_SHELTERS,ORIGINS,SCENARIOS,SHELTER_POSITIONS,VARIANTS,simulate_route


def layout():
    initial = simulate_route(active=False)
    return html.Div([
        html.Div([
            html.Div([html.H1(['Zelo avisa. ',html.Em('Você se orienta.')]),
                      html.P('Ruas do centro de São Paulo. Alagamentos, localização e abrigos simulados.',className='description')]),
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
                html.Label('Desenho das áreas alagadas',htmlFor='sim-variant'),
                html.Select([html.Option(label,value=key) for key,label in VARIANTS.items()],id='sim-variant',className='sim-select'),
                html.Div([
                    html.Span('Posições dos três abrigos',className='sim-control-label'),
                    *[html.Div([
                        html.Label(letter,htmlFor=f'sim-shelter-{letter.lower()}',className='sim-shelter-letter'),
                        html.Select([html.Option(label,value=key,selected=key==position)
                                     for key,(_,label) in SHELTER_POSITIONS.items()],
                                    id=f'sim-shelter-{letter.lower()}',className='sim-select',
                                    **{'aria-label':f'Posição do abrigo {letter}'}),
                    ],className='sim-shelter-control') for letter,position in zip('ABC',DEFAULT_SHELTERS)],
                ],className='sim-shelter-controls'),
                html.P('Escolha posições diferentes. A rota prioriza menor exposição, mesmo que seja mais longa.',className='description',id='sim-position-help'),
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
                    html.P('Alagamentos bloqueiam os trechos; a distância só desempata rotas com a mesma exposição.',
                           id='sim-exposure',className='description'),
                    html.Div(id='sim-shelter-status',className='sim-shelter-status'),
                ],className='sim-result',**{'aria-live':'polite'}),
                html.Button('Repetir aviso',id='sim-repeat',className='button sim-repeat',disabled=True,**{'data-sim-action':'replay'}),
                html.P('Rota demonstrativa. Não use este cenário para uma evacuação real.',className='description sim-footnote'),
            ],className='sim-controls'),
            html.Section([
              html.Div([
                html.Div(id='simulator-map',className='sim-map',role='img',**{'aria-label':'Mapa fixo do recorte da simulação, com ruas, áreas alagadas e três abrigos'}),
                html.Div([
                    html.Span([html.I(className='legend-dot user'),'Você (simulado)']),
                    html.Span([html.I(className='legend-dot risk'),'Área simulada']),
                    html.Span([html.I(className='legend-dot caution'),'Proximidade']),
                    html.Span([html.I(className='legend-dot route'),'Rota sugerida']),
                ],className='sim-map-legend'),
                html.Span('Recorte fixo · centro de São Paulo',className='sim-map-crop-label'),
                html.Span('© OpenStreetMap contributors · Ruas: ODbL. Alagamentos e abrigos simulados.',className='sim-map-note'),
              ],className='sim-map-frame'),
              html.Aside([
                html.Div([html.Strong('Alerta simulado'),
                          html.Span('O Zelo está calculando um trajeto com menor exposição.',id='sim-alert-text')],
                         className='sim-alert-banner',id='sim-alert',role='alert',hidden=True),
                html.Div([
                    html.Div(className='phone-island'),
                    html.Div([html.Span('Z',className='phone-brand'),html.Div([html.Strong('Zelo'),html.Span('Seu assistente',className='description')])],className='phone-header'),
                    html.Div([
                        html.Span('DEMONSTRAÇÃO',className='phone-demo-tag'),
                        html.Div('Seu dia, com mais cuidado.',id='sim-phone-title',className='phone-message-title'),
                        html.P('Receba o aviso e acompanhe a rota no mapa.',id='sim-phone-message'),
                        html.Div([html.Span('↗'),html.P('Seu caminho será exibido no mapa.',id='sim-phone-route')],className='phone-route'),
                        html.Span('Vibração representada na animação',className='description phone-vibration-note'),
                    ],className='phone-screen'),
                    html.Div(className='phone-home-indicator'),
                    html.Span(')))',className='phone-sound-wave',**{'aria-hidden':'true'}),
                ],className='sim-phone',id='sim-phone',role='img',**{'aria-label':'Celular demonstrativo do Zelo, com animação de vibração ao receber um aviso'}),
                html.P('Primeiro, evitar o alagamento. Depois, reduzir a exposição no caminho.',className='description sim-priority-note'),
              ],className='sim-device-dock'),
            ],className='sim-map-stage'),
        ],className='simulator-workspace'),
        html.Dialog([
            html.Div([html.H2('Como funciona esta demonstração'),html.Button('×',className='dialog-close',
                      **{'aria-label':'Fechar informações da simulação','data-close-dialog':'simulator-information'})],className='dialog-header'),
            html.Div([
                html.P('O mapa tem enquadramento fixo no centro de São Paulo, sem arrastar ou aproximar. A rede de caminhos vem do OpenStreetMap, preservando curvas e cruzamentos. É um recorte de circulação a pé, sem validação operacional de acessos, escadas ou restrições atuais. Não solicita geolocalização.'),
                html.P('As bases de precipitação do projeto são observações históricas. As áreas de alagamento e os abrigos deste cenário foram criados para a demonstração; não são previsões nem locais operacionais confirmados.'),
                html.P('Há três variações de contorno dos alagamentos e três abrigos A, B e C, cada um com nove posições possíveis. As posições precisam ser diferentes. Mudar uma escolha reinicia o cenário.'),
                html.P('Dijkstra remove qualquer trecho que entre ou toque uma área alagada. Entre os caminhos restantes, minimiza primeiro a soma de distância × exposição: peso didático 0,65 a menos de 35 m da área; 0,30 entre 35 e 90 m; zero mais longe. A distância total só desempata exposições iguais. Esses pesos não são probabilidades calibradas. Um abrigo isolado não é escolhido; se nenhum for acessível, não se desenha rota.'),
                html.P('O áudio é breve e começa após o clique. A vibração física depende do navegador e do aparelho; a animação funciona também no computador. O botão Reiniciar interrompe os efeitos.'),
                html.P('O mapa de fundo usa OpenStreetMap quando há conexão. A rede demonstrativa continua visível se os blocos do mapa não carregarem.',className='description'),
            ],className='dialog-body'),
        ],id='simulator-information',className='zelo-dialog',**{'aria-label':'Como funciona esta demonstração'}),
    ],id='simulator-root',className='simulator-page',**{'data-initial-scene':json.dumps(initial,ensure_ascii=False)})
