"""Elementos visuais compartilhados pelas páginas do Zelo."""

from urllib.parse import quote

from dash import html


PATHS = {
    "home": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',
    "alert": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
    "health": '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
    "general": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "water": '<path d="M12 3c-2 3-6 7-6 11a6 6 0 0 0 12 0c0-4-4-8-6-11Z"/><path d="M9 16a3 3 0 0 0 3 2"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 10v10M3 15h18"/>',
    "arrow": '<path d="M5 12h14m-5-5 5 5-5 5"/>',
    "external": '<path d="M14 3h7v7M21 3l-11 11"/><path d="M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "chevron-left": '<path d="m14 5-7 7 7 7"/>',
    "chevron-right": '<path d="m10 5 7 7-7 7"/>',
    "first": '<path d="M5 5v14m13-14-7 7 7 7"/>',
    "last": '<path d="M19 5v14M6 5l7 7-7 7"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
}


def icon(name, color="#688296", class_name=""):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
           f'{PATHS[name]}</svg>')
    return html.Img(src="data:image/svg+xml," + quote(svg), alt="", className="icon " + class_name,
                    **{"aria-hidden": "true"})


def format_int(value):
    return f"{value:,}".replace(",", ".")
