"""Apresentação do assistente virtual Zelo e acesso às suas áreas de dados."""

from dash import dcc, html

from shared.components import icon


def layout():
    return html.Div([
        html.Section([
            html.Div([html.Span(className="status-dot"), "Assistente virtual para o cidadão"], className="eyebrow"),
            html.H1(["Toda consulta importa. ", html.Em("Todo cidadão também.")]),
            html.P("O Zelo propõe apoiar o acompanhamento de consultas no SUS, com módulos de avisos de enchentes e apoio aos deslocamentos. Explore as bases públicas do estudo de caso.",
                   className="description home-description"),
            html.Div([
                _area("Saúde", "Faltas, espera por exames, hospitais, leitos, ouvidoria e telessaúde.",
                      "Consultar dados do SUS", "/saude", "health", "Fontes estaduais, municipais e federais"),
                _area("Enchentes", "Chuva acumulada e índices de precipitação por município.",
                      "Consultar dados de chuva", "/enchentes", "water", "Setembro e outubro de 2025"),
                _area("Mobilidade", "Frota ativa e registros de sinistros, pessoas e veículos.",
                      "Consultar dados de mobilidade", "/mobilidade", "bus", "Bases históricas de 2025 e 2026"),
                _area("Visão geral", "Saúde, enchentes e mobilidade reunidas na mesma tela.",
                      "Abrir visão geral", "/geral", "general", "Consulta das três áreas"),
            ], className="area-grid"),
        ], className="panel welcome-panel"),
        html.Section([
            html.Div([html.Div([icon("table", "#298f79"), html.H2("Uma consulta mais próxima dos dados")], className="section-heading"),
                      html.Span("Como explorar", className="small-badge")], className="panel-heading"),
            html.Div([
                _step("01", "Escolha uma base", "As abas reúnem os arquivos de cada área e seus períodos de referência."),
                _step("02", "Encontre um registro", "Use a busca, altere a ordenação e percorra as páginas da tabela."),
                _step("03", "Consulte o arquivo completo", "Baixe o CSV da base selecionada para avaliar todos os campos."),
            ], className="steps"),
        ], className="panel guide-panel"),
        html.Div([icon("check", "#299d81"), html.Span("Conteúdo original preservado"),
                  html.Span("Os arquivos compactados mantêm todos os registros das bases públicas.", className="description")],
                 className="integrity-note"),
    ], className="home-page")


def _area(title, description, action, href, symbol, period):
    return dcc.Link([
        html.Div([html.Span(icon(symbol, "#24997d"), className="area-symbol"),
                  icon("arrow", "#7b91a1")], className="area-top"),
        html.H2(title), html.P(description, className="description"),
        html.Span(period, className="description area-period"),
        html.Span([action, icon("chevron-right", "#20886f")], className="area-action"),
    ], href=href, className="area-card")


def _step(number, title, description):
    return html.Div([html.Span(number, className="step-number"),
                     html.Div([html.Strong(title), html.P(description, className="description")])], className="step")
