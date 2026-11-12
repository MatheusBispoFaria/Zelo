"""Entrada do dashboard Zelo. Execute com: python app.py."""

import gzip
import os
from pathlib import Path

from dash import Dash, Input, Output, dcc, html
from flask import Response, abort, send_file, stream_with_context

import flood
import general
import health
import home
import mobility
from shared.components import icon
from shared.data_access import DATA_DIR, DATASETS, metadata
from shared.data_view import register_callbacks


ROOT = Path(__file__).resolve().parent
PAGES = {"/": ("Início", home.layout), "/geral": ("Visão geral", general.layout),
         "/saude": ("Saúde e SUS", health.layout), "/enchentes": ("Enchentes", flood.layout),
         "/mobilidade": ("Mobilidade", mobility.layout)}
NAVIGATION = [("/", "Início", "home", "home"), ("/geral", "Visão geral", "general", "general"),
              ("/saude", "Saúde", "health", "health"), ("/enchentes", "Enchentes", "water", "flood"),
              ("/mobilidade", "Mobilidade", "bus", "mobility")]


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
            html.Aside([
                dcc.Link([html.Span("Z", className="brand-mark", **{"aria-hidden": "true"}),
                          html.Span("Zelo · Início", className="sr-only")], href="/", className="brand", title="Zelo · Início"),
                html.Nav([dcc.Link([icon(symbol, "#e8efeb"), html.Span(label, className="sr-only")],
                                   href=href, id=f"rail-{key}", className="rail-link", title=label)
                          for href, label, symbol, key in NAVIGATION],
                         className="rail-nav", **{"aria-label": "Navegação lateral"}),
                html.Div([html.Span("SP", className="state-mark")], className="rail-bottom", title="São Paulo"),
            ], className="sidebar"),
            html.Div([
                html.Header([
                    html.Div([html.Button(icon("menu"), id="menu-toggle", n_clicks=0, className="menu-button button",
                                          title="Recolher ou mostrar menu lateral", **{"aria-label": "Alternar menu lateral"}),
                              dcc.Link("Zelo", href="/", className="brand-name"),
                              html.Span("/", className="breadcrumb-divider"),
                              html.Span("Painel do cidadão", className="breadcrumb-section"),
                              html.Span("/", className="breadcrumb-divider breadcrumb-section"),
                              html.Span("Início", id="breadcrumb-current")], className="breadcrumb"),
                    dcc.Link(["Fontes e método", icon("external")], href="/geral#fontes",
                             className="source-link"),
                ], className="topbar"),
                html.Main(home.layout(), id="page-content", className="main-content", tabIndex=-1),
                html.Footer([html.Span("Zelo"), html.Span("Dados públicos · Fontes estaduais, municipais e federais", className="description")],
                            className="app-footer"),
            ], className="workspace"),
        ], id="app-shell", className="app-shell"),
    ])

    @application.callback(
        Output("page-content", "children"), Output("breadcrumb-current", "children"),
        *[Output(f"rail-{key}", "className") for _, _, _, key in NAVIGATION],
        Input("url", "pathname"),
    )
    def route(pathname):
        path = (pathname or "/").rstrip("/") or "/"
        if path not in PAGES:
            page = html.Section([html.H1("Página não encontrada"),
                                 dcc.Link("Voltar para o início", href="/", className="button")], className="panel missing-page")
            return (page, "Página não encontrada", *["rail-link"] * len(NAVIGATION))
        title, view = PAGES[path]
        rails = ["rail-link active" if href == path else "rail-link" for href, *_ in NAVIGATION]
        return (view(), title, *rails)

    @application.callback(Output("app-shell", "className"), Input("menu-toggle", "n_clicks"))
    def collapse_menu(clicks):
        return "app-shell is-compact" if (clicks or 0) % 2 else "app-shell"

    register_callbacks(application, "flood")
    register_callbacks(application, "mobility")
    register_callbacks(application, "health")
    general.register_callbacks(application)

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

    return application


app = create_app()
server = app.server


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8050")), debug=False)
