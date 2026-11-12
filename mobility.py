"""Consulta às bases históricas de frota e sinistros de trânsito."""

from data_view import dataset_view


def layout():
    return dataset_view("mobility", "Mobilidade", "bus",
                        "Consulte as bases de sinistros, pessoas envolvidas, veículos e frota ativa.",
                        "As bases são históricas e não informam a localização de ônibus em tempo real.")
