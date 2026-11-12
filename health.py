"""Consulta das bases públicas relacionadas ao SUS e ao acesso à saúde."""

from shared.data_view import dataset_view


def layout(*, heading_level=1):
    return dataset_view("health", "Saúde e SUS", "health",
                        "Consulte faltas, espera por exames, hospitais e leitos, ouvidorias e produção de telessaúde.",
                        "As abrangências variam entre capital, unidades estaduais e Brasil. A consulta preserva os dados recebidos; a base hospitalar registra capacidade cadastrada.",
                        heading_level=heading_level)
