"""Consulta reutilizada pelas páginas de enchentes e mobilidade."""

import csv
import logging
import sqlite3

from dash import Input, Output, State, ctx, dcc, html

from components import format_int, icon
from data_access import DATASETS, metadata, query_page

logger = logging.getLogger(__name__)


def dataset_view(scope, title, symbol, description, note):
    keys = [key for key, config in DATASETS.items() if config["group"] == scope]
    selected = keys[0]
    meta = metadata(selected)
    column_options = [{"label": name, "value": name} for name in meta["columns"]]
    return html.Div([
        html.Div([
            html.Div([html.Span(icon(symbol, "#278e77"), className="page-symbol"),
                      html.Div([html.H1(title), html.P(description, className="description")])], className="page-heading"),
            html.Span("Consulta de dados", className="small-badge"),
        ], className="page-intro"),
        html.Section([
            dcc.RadioItems(id=f"{scope}-dataset", options=[{"label": DATASETS[key]["label"], "value": key} for key in keys],
                           value=selected, className="dataset-tabs", inputClassName="dataset-radio", labelClassName="dataset-tab"),
            html.Div([
                html.Div([html.H2(id=f"{scope}-table-title", children=meta["title"]),
                          html.P(id=f"{scope}-meta", children=_meta_text(meta), className="description")], className="table-heading-copy"),
                html.A([icon("download", "#227e68"), "Baixar CSV"], id=f"{scope}-download",
                       href=f"/download/{selected}", className="button button-download"),
            ], className="table-heading"),
            html.Div([
                html.Div([html.Label("Buscar registros", htmlFor=f"{scope}-search"),
                          html.Div([icon("search"), dcc.Input(id=f"{scope}-search", type="search", value="", debounce=0.5,
                                                            placeholder="Digite um município, código ou valor…", maxLength=200,
                                                            className="search-input")], className="search-control")], className="search-field"),
                html.Div([html.Label("Campo de busca", id=f"{scope}-search-label"),
                          dcc.Dropdown(id=f"{scope}-search-column", options=[{"label": "Todos os campos", "value": "__all__"}, *column_options],
                                       value="__all__", clearable=False, searchable=True,
                                       className="zelo-select")], className="field", role="group",
                         **{"aria-labelledby": f"{scope}-search-label"}),
                html.Div([html.Label("Ordenar por", id=f"{scope}-sort-label"),
                          dcc.Dropdown(id=f"{scope}-sort", options=[{"label": "Ordem original", "value": "__original__"}, *column_options],
                                       value="__original__", clearable=False, searchable=True,
                                       className="zelo-select")], className="field", role="group",
                         **{"aria-labelledby": f"{scope}-sort-label"}),
                html.Button("↑ Crescente", id=f"{scope}-order", n_clicks=0, className="button order-button",
                            title="Alternar entre ordenação crescente e decrescente"),
            ], className="table-tools"),
            dcc.Store(id=f"{scope}-state", data={"page": 0, "descending": False, "dataset": selected}),
            dcc.Loading(html.Div(id=f"{scope}-table", className="table-result", **{"aria-live": "polite"}),
                        type="circle", color="#2aab8b", delay_show=200,
                        overlay_style={"visibility": "visible", "opacity": 0.35}, parent_className="table-loading"),
            html.Div([
                html.Span(id=f"{scope}-range", className="record-range", **{"aria-live": "polite"}),
                html.Div([html.Label("Linhas por página", id=f"{scope}-size-label"),
                          dcc.Dropdown(id=f"{scope}-size", options=[25, 50, 100], value=25, clearable=False,
                                       searchable=False, className="zelo-select page-size-select")], className="page-size", role="group",
                         **{"aria-labelledby": f"{scope}-size-label"}),
                html.Div([
                    _page_button(scope, "first", "Primeira página", "first"),
                    _page_button(scope, "previous", "Página anterior", "chevron-left"),
                    html.Span(id=f"{scope}-page-label", className="page-label"),
                    _page_button(scope, "next", "Próxima página", "chevron-right"),
                    _page_button(scope, "last", "Última página", "last"),
                ], className="pagination"),
            ], className="table-footer"),
        ], className="panel data-panel"),
        html.Div([html.Span(className="status-dot"), html.P(note, className="description")], className="data-note"),
    ], className="data-page")


def _meta_text(meta):
    return f"{meta['period']} · {format_int(meta['rows'])} registros · {len(meta['columns'])} campos · {meta['source']}"


def _page_button(scope, action, label, symbol):
    return html.Button(icon(symbol), id=f"{scope}-{action}", n_clicks=0, className="button page-button",
                       title=label, disabled=True, **{"aria-label": label})


def render_table(result):
    if not result["rows"]:
        return html.Div([icon("search", "#6c8799"), html.H2("Nenhum registro encontrado"),
                         html.P("Tente outro termo ou escolha um campo de busca diferente.", className="description")],
                        className="empty-state")
    columns = result["columns"]
    offset = result["page"] * result["page_size"]
    return html.Div(html.Table([
        html.Thead(html.Tr([html.Th("#", scope="col", className="row-number"),
                            *[html.Th(name, scope="col", title=name) for name in columns]])),
        html.Tbody([html.Tr([html.Td(format_int(offset + number + 1), className="row-number"),
                            *[html.Td(row[name], title=row[name]) for name in columns]])
                    for number, row in enumerate(result["rows"])]),
    ], className="data-table"), className="table-scroll", tabIndex=0,
        **{"role": "region", "aria-label": "Registros da base selecionada. Role horizontalmente para consultar todos os campos."})


def register_callbacks(app, scope):
    @app.callback(
        Output(f"{scope}-search-column", "options"), Output(f"{scope}-search-column", "value"),
        Output(f"{scope}-sort", "options"), Output(f"{scope}-sort", "value"),
        Output(f"{scope}-table-title", "children"), Output(f"{scope}-meta", "children"),
        Output(f"{scope}-download", "href"), Input(f"{scope}-dataset", "value"),
    )
    def update_dataset(key):
        if key not in DATASETS or DATASETS[key]["group"] != scope:
            key = next(key for key, value in DATASETS.items() if value["group"] == scope)
        meta = metadata(key)
        fields = [{"label": name, "value": name} for name in meta["columns"]]
        return ([{"label": "Todos os campos", "value": "__all__"}, *fields], "__all__",
                [{"label": "Ordem original", "value": "__original__"}, *fields], "__original__",
                meta["title"], _meta_text(meta), f"/download/{key}")

    @app.callback(
        Output(f"{scope}-table", "children"), Output(f"{scope}-range", "children"),
        Output(f"{scope}-page-label", "children"), Output(f"{scope}-state", "data"),
        Output(f"{scope}-first", "disabled"), Output(f"{scope}-previous", "disabled"),
        Output(f"{scope}-next", "disabled"), Output(f"{scope}-last", "disabled"),
        Output(f"{scope}-order", "children"),
        Input(f"{scope}-dataset", "value"), Input(f"{scope}-search", "value"),
        Input(f"{scope}-search-column", "value"), Input(f"{scope}-sort", "value"),
        Input(f"{scope}-size", "value"), Input(f"{scope}-order", "n_clicks"),
        Input(f"{scope}-first", "n_clicks"), Input(f"{scope}-previous", "n_clicks"),
        Input(f"{scope}-next", "n_clicks"), Input(f"{scope}-last", "n_clicks"),
        State(f"{scope}-state", "data"),
    )
    def update_table(key, search, search_column, sort, size, order_clicks, first, previous, next_, last, state):
        if key not in DATASETS or DATASETS[key]["group"] != scope:
            key = next(key for key, value in DATASETS.items() if value["group"] == scope)
        state = state or {"page": 0, "descending": False, "dataset": key}
        trigger = ctx.triggered_id
        page = state.get("page", 0)
        descending = state.get("descending", False)
        if state.get("dataset") != key:
            descending = False
            page = 0
        if trigger == f"{scope}-order":
            descending = not descending
            page = 0
        elif trigger == f"{scope}-previous":
            page -= 1
        elif trigger == f"{scope}-next":
            page += 1
        elif trigger == f"{scope}-last":
            page = 10 ** 12
        elif trigger == f"{scope}-first":
            page = 0
        elif trigger not in (f"{scope}-order",):
            page = 0
        meta = metadata(key)
        # A troca de base também troca os campos disponíveis no mesmo ciclo da interface.
        search_column = search_column if search_column in meta["columns"] else "__all__"
        sort = sort if sort in meta["columns"] else "__original__"
        try:
            result = query_page(key, page=page, page_size=size or 25, search=search,
                                search_column=search_column, sort_column=sort, descending=descending)
            start = result["page"] * result["page_size"] + 1 if result["total"] else 0
            end = start + len(result["rows"]) - 1 if result["total"] else 0
            total_label = f"{format_int(start)}–{format_int(end)} de {format_int(result['total'])} registros"
            page_label = f"{format_int(result['page'] + 1)} / {format_int(result['last_page'] + 1)}"
            state = {"page": result["page"], "descending": descending, "dataset": key}
            beginning = result["page"] == 0
            ending = result["page"] == result["last_page"]
            return (render_table(result), total_label, page_label, state,
                    beginning, beginning, ending, ending, "↓ Decrescente" if descending else "↑ Crescente")
        except (OSError, ValueError, csv.Error, sqlite3.Error):
            logger.exception("Falha na consulta da base %s", key)
            error = html.Div([html.H2("Não foi possível abrir esta base"),
                              html.P("Confira se o arquivo compactado e o manifesto estão na pasta data e tente novamente.",
                                     className="description")], className="empty-state", role="alert")
            return error, "Consulta indisponível", "—", state, True, True, True, True, "↑ Crescente"
