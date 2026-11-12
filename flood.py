"""Consulta às bases municipais de precipitação, sem estimativas nesta etapa."""

from data_view import dataset_view


def layout():
    return dataset_view("flood", "Enchentes", "water",
                        "Consulte os registros municipais de chuva acumulada e dos índices de precipitação.",
                        "Os períodos das bases são históricos. Campos e valores são apresentados como nos arquivos de origem.")
