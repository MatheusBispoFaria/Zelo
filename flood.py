"""Consulta das ocorrências hidrológicas e das bases de precipitação do acervo."""

from shared.data_view import dataset_view


def layout(*, heading_level=1):
    return dataset_view("flood", "Enchentes", "water",
                        "Consulte alagamentos e inundações de 2024–2026, chuva municipal de 2025 e estações horárias de 2026.",
                        "Ocorrências: capital paulista; chuva municipal: estado de SP; INMET: estações de todo o Brasil, com SP como seleção inicial. Os valores permanecem como na fonte.",
                        heading_level=heading_level)
