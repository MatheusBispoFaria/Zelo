"""Entrada do dashboard Zelo. Execute com: python app.py."""

import gzip
import os
from pathlib import Path

from dash import Dash, Input, Output, dcc, html
from flask import Response, abort, jsonify, request, send_file, stream_with_context

import flood
import general
import health
import home
import simulator
from shared.components import icon
from shared.data_access import AUXILIARY, DATA_DIR, DATASETS, metadata
from shared.data_view import register_callbacks
from shared.simulation import DEFAULT_SHELTERS, simulate_route


ROOT = Path(__file__).resolve().parent
PAGES = {"/": ("Início", home.layout), "/geral": ("Visão geral", general.layout),
         "/saude": ("Saúde e SUS", health.layout), "/enchentes": ("Enchentes", flood.layout),
         "/simulador": ("Simulador de alerta", simulator.layout)}
NAVIGATION = [("/", "Início", "home", "home"), ("/geral", "Visão geral", "general", "general"),
              ("/saude", "Saúde", "health", "health"), ("/enchentes", "Enchentes", "water", "flood"),
              ("/simulador", "Simulador", "alert", "simulator")]


def page_view(builder, path):
    page = builder()
    page.key = path
    setattr(page, "data-page", path)
    return page


def create_app():
    application = Dash(__name__, assets_folder=str(ROOT / "assets"),
                       title="Zelo · Cuidado e dados", update_title="Carregando…",
                       suppress_callback_exceptions=True,
                       meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
    application.index_string = application.index_string.replace("<html>", '<html lang="pt-BR">')
    application.layout = html.Div([
        dcc.Location(id="url", refresh=False),
        html.A("Ir para o conteúdo", href="#page-content", className="skip-link"),
        html.Div([
            html.Div(className="sidebar-reveal-edge", **{"aria-hidden": "true"}),
            html.Span("Clique no Menu para expandir", id="menu-hint", className="menu-hint", role="tooltip"),
            html.Aside([
                dcc.Link([html.Span("Z", className="brand-mark", **{"aria-hidden": "true"}),
                          html.Span("Zelo · Início", className="sr-only")], href="/", className="brand", title="Zelo · Início"),
                html.Nav([dcc.Link([icon(symbol, "#e8efeb"), html.Span(label, className="sr-only")],
                                   href=href, id=f"rail-{key}", className="rail-link", title=label)
                          for href, label, symbol, key in NAVIGATION],
                         className="rail-nav", **{"aria-label": "Navegação lateral"}),
                html.Div([html.Span("SP", className="state-mark")], className="rail-bottom", title="São Paulo"),
            ], id="primary-sidebar", className="sidebar"),
            html.Div([
                html.Header([
                    html.Div([html.Button(icon("menu"), id="menu-toggle", n_clicks=0, className="menu-button button",
                                          title="Expandir menu lateral", **{"aria-label": "Alternar menu lateral",
                                                                          "aria-controls": "primary-sidebar", "aria-expanded": "false",
                                                                          "aria-describedby": "menu-hint"}),
                              dcc.Link("Zelo", href="/", className="brand-name"),
                              html.Span("/", className="breadcrumb-divider"),
                              html.Span("Painel do cidadão", className="breadcrumb-section"),
                              html.Span("/", className="breadcrumb-divider breadcrumb-section"),
                              html.Span("Início", id="breadcrumb-current")], className="breadcrumb"),
                    dcc.Link(["Fontes e método", icon("external")], href="/geral#fontes",
                             className="source-link"),
                ], className="topbar"),
                html.Main(page_view(home.layout, "/"), id="page-content", className="main-content", tabIndex=-1),
                html.Footer([html.Span("Zelo"), html.Span("Dados públicos · Fontes estaduais, municipais e federais", className="description")],
                            className="app-footer"),
            ], id="app-workspace", className="workspace"),
        ], id="app-shell", className="app-shell is-collapsed"),
    ])

    @application.callback(
        Output("page-content", "children"), Output("breadcrumb-current", "children"),
        Output("app-workspace", "className"),
        *[Output(f"rail-{key}", "className") for _, _, _, key in NAVIGATION],
        Input("url", "pathname"),
    )
    def route(pathname):
        path = (pathname or "/").rstrip("/") or "/"
        if path not in PAGES:
            page = html.Section([html.H1("Página não encontrada"),
                                 dcc.Link("Voltar para o início", href="/", className="button")], className="panel missing-page",
                                key=path, **{"data-page":path})
            return (page, "Página não encontrada", "workspace", *["rail-link"] * len(NAVIGATION))
        title, view = PAGES[path]
        rails = ["rail-link active" if href == path else "rail-link" for href, *_ in NAVIGATION]
        workspace = "workspace workspace-general" if path == "/geral" else "workspace"
        return (page_view(view, path), title, workspace, *rails)

    @application.callback(Output("app-shell", "className"), Output("menu-toggle", "aria-expanded"),
                          Output("menu-toggle", "title"), Input("menu-toggle", "n_clicks"))
    def collapse_menu(clicks):
        if (clicks or 0) % 2:
            return "app-shell", "true", "Recolher menu lateral"
        return "app-shell is-collapsed", "false", "Expandir menu lateral"

    register_callbacks(application, "flood")
    register_callbacks(application, "health")
    general.register_callbacks(application)

    @application.server.get('/api/simulator/route')
    def simulator_route():
        try:
            result = simulate_route(request.args.get('scenario','localizado'), request.args.get('origin','casa'),
                                    variant=request.args.get('variant','1'),
                                    shelter_positions=[request.args.get(f'shelter_{letter}',default)
                                                       for letter,default in zip('abc',DEFAULT_SHELTERS)])
        except ValueError as error:
            return jsonify({'error':str(error)}),400
        response = jsonify(result)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @application.server.get("/download/<key>")
    def download_csv(key):
        if key not in DATASETS:
            abort(404)
        info = metadata(key)
        source = DATA_DIR / info["file"]
        if not source.is_file():
            abort(404)

        @stream_with_context
        def chunks():
            with gzip.open(source, "rb") as stream:
                for block in iter(lambda: stream.read(256 * 1024), b""):
                    yield block

        encoding = "windows-1252" if info["csv_options"]["encoding"] == "cp1252" else "utf-8"
        return Response(chunks(), headers={"Content-Disposition": f'attachment; filename="{info["source"]}"',
                                            "Content-Type": f"text/csv; charset={encoding}",
                                            "X-Content-Type-Options": "nosniff"})

    @application.server.get("/download/<key>/gzip")
    def download_gzip(key):
        if key not in DATASETS:
            abort(404)
        source = DATA_DIR / DATASETS[key]["file"]
        if not source.is_file():
            abort(404)
        return send_file(source, as_attachment=True, download_name=source.name)

    @application.server.get("/download-asset/<key>")
    def download_auxiliary(key):
        if key not in AUXILIARY:abort(404)
        source=DATA_DIR/AUXILIARY[key]["file"]
        if not source.is_file():abort(404)
        return send_file(source,as_attachment=True,download_name=source.name)

    return application


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8050")), debug=False)
