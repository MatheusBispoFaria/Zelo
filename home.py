"""Apresentação do assistente virtual Zelo e acesso às suas áreas de dados."""

from dash import dcc, html

from shared.components import icon


def layout():
    return html.Div([
        html.Header([
            html.Div([html.Span(className="status-dot"), "Assistente virtual para o cidadão"], className="eyebrow"),
            html.H1(["Toda consulta importa. ", html.Em("Todo cidadão também.")]),
            html.P("O Zelo propõe apoiar o acompanhamento de consultas no SUS, com avisos de enchentes. Explore as bases públicas do estudo de caso.",
                   className="description home-description"),
        ], className="home-intro"),
        html.Div([
            html.P("Passe o mouse ou use o teclado para explorar. No celular, toque para revelar e toque novamente para abrir.",
                   className="description home-explore-hint"),
            html.Nav([
                _portal("Saúde", "Faltas, espera por exames e acesso ao SUS nas bases públicas.",
                        "/saude", "health", "health"),
                _portal("Enchentes", "Ocorrências de alagamento, inundações e registros de chuva.",
                        "/enchentes", "water", "flood"),
                _portal("Visão geral", "Explore as perguntas do estudo com gráficos e filtros.",
                        "/geral", "general", "general"),
                _portal("Simulador", "Receba um alerta e acompanhe uma rota que evita as áreas alagadas.",
                        "/simulador", "alert", "simulator"),
            ],className="home-portals",**{"aria-label":"Áreas do Zelo"}),
        ],className="home-explore"),
        html.Div([icon("check", "#299d81"), html.Span("Conteúdo original preservado"),
                  html.Span("Os arquivos compactados mantêm todos os registros das bases públicas.", className="description")],
                 className="integrity-note"),
    ], className="home-page")


def _portal(title, description, href, symbol, tone):
    return dcc.Link([
        html.Span(icon(symbol,"#173c32" if tone in ("general","simulator") else "#f0f5ea"),className="portal-symbol"),
        html.Div([html.H2(title),
                  html.P(description,id=f"home-intro-{tone}",className="description"),
                  html.Span(["Explorar",icon("arrow","#173c32" if tone in ("general","simulator") else "#f0f5ea")],
                            className="portal-action")],className="portal-copy"),
    ],href=href,className=f"home-portal portal-{tone}",id=f"home-{tone}")
