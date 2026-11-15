#!/usr/bin/env python3
"""Gera o Diagrama Entidade-Relacionamento (docs/der.png) e o Mapa do Recorte (docs/mapa_recorte.png)."""

import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from shapely.geometry import shape

BASE_DIR = Path(__file__).resolve().parent.parent
PROC_DIR = BASE_DIR / "dados" / "tratados"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def gerar_der() -> None:
    fig, ax = plt.subplots(figsize=(13, 8.2), dpi=250)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_table(x, y, w, title, subtitle, cols, header_color="#1f4e78"):
        row_h = 3.2
        header_h = 6.0
        total_h = header_h + len(cols) * row_h + 1.2

        # Caixa principal
        rect = mpatches.FancyBboxPatch(
            (x, y - total_h), w, total_h,
            boxstyle="round,pad=0.3,rounding_size=0.8",
            linewidth=1.4, edgecolor=header_color, facecolor="#ffffff",
        )
        ax.add_patch(rect)

        # Cabeçalho
        hdr = mpatches.FancyBboxPatch(
            (x, y - header_h), w, header_h,
            boxstyle="round,pad=0.3,rounding_size=0.8",
            linewidth=0, facecolor=header_color,
        )
        ax.add_patch(hdr)
        ax.text(x + w / 2, y - 2.3, title, ha="center", va="center",
                color="white", fontsize=10.5, fontweight="bold", family="monospace")
        ax.text(x + w / 2, y - 4.7, subtitle, ha="center", va="center",
                color="#dce6f1", fontsize=7.5)

        for idx, (col_name, col_type, badge) in enumerate(cols):
            cy = y - header_h - 1.8 - idx * row_h
            if badge:
                ax.text(x + 1.0, cy, badge, ha="left", va="center",
                        fontsize=7.2, fontweight="bold",
                        color="#b45309" if "PK" in badge else "#0f766e", family="monospace")
            ax.text(x + 6.2, cy, col_name, ha="left", va="center",
                    fontsize=8.3, color="#111827", family="monospace")
            ax.text(x + w - 1.0, cy, col_type, ha="right", va="center",
                    fontsize=7.6, color="#4b5563", family="monospace")

        return (x, y - total_h, w, total_h)

    # Desenhar as 4 tabelas
    draw_table(
        4, 92, 39,
        "municipio", "Espacial · MultiPolygon · SRID 4674",
        [
            ("cod_ibge", "INTEGER NOT NULL", "PK"),
            ("nome", "VARCHAR(100) NOT NULL", ""),
            ("uf", "CHAR(2) NOT NULL", ""),
            ("regiao_imediata", "VARCHAR(60) NOT NULL", ""),
            ("area_km2", "NUMERIC(12,3) NOT NULL", ""),
            ("populacao_2022", "INTEGER", ""),
            ("geom", "GEOMETRY(MultiPolygon,4674)", "GiST"),
        ],
        header_color="#1e3a8a",
    )

    draw_table(
        56, 92, 40,
        "equipamento_urbano", "Espacial · Point · SRID 4674",
        [
            ("id_equipamento", "SERIAL NOT NULL", "PK"),
            ("osm_id", "BIGINT NOT NULL", "UQ"),
            ("nome", "VARCHAR(150) NOT NULL", ""),
            ("tipo_osm", "VARCHAR(50) NOT NULL", ""),
            ("id_categoria", "SMALLINT NOT NULL", "FK"),
            ("cod_ibge", "INTEGER NOT NULL", "FK"),
            ("bairro_ou_localidade", "VARCHAR(120)", ""),
            ("operador", "VARCHAR(120)", ""),
            ("geom", "GEOMETRY(Point,4674)", "GiST"),
        ],
        header_color="#0f766e",
    )

    draw_table(
        56, 42, 40,
        "categoria_equipamento", "Domínio · Sem geometria",
        [
            ("id_categoria", "SMALLINT NOT NULL", "PK"),
            ("codigo", "VARCHAR(30) NOT NULL", "UQ"),
            ("nome", "VARCHAR(60) NOT NULL", ""),
            ("descricao", "VARCHAR(200) NOT NULL", ""),
        ],
        header_color="#475569",
    )

    draw_table(
        4, 46, 39,
        "trecho_viario", "Espacial · MultiLineString · SRID 4674",
        [
            ("id_trecho", "SERIAL NOT NULL", "PK"),
            ("osm_id", "BIGINT NOT NULL", "UQ"),
            ("codigo_rodovia", "VARCHAR(30)", ""),
            ("nome", "VARCHAR(150)", ""),
            ("classe_via", "VARCHAR(30) NOT NULL", ""),
            ("pavimentado", "BOOLEAN", ""),
            ("extensao_km", "NUMERIC(10,3) NOT NULL", ""),
            ("geom", "GEOMETRY(MultiLineString,4674)", "GiST"),
        ],
        header_color="#7c2d12",
    )

    # Relacionamento FK: municipio (1) -> equipamento_urbano (N)
    ax.annotate("", xy=(55.6, 80.5), xytext=(43.4, 80.5),
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#1e3a8a"))
    ax.text(49.5, 83.2, "FK 1:N\ncod_ibge", ha="center", va="center",
            fontsize=7.8, color="#1e3a8a", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="#eff6ff", ec="#93c5fd"))

    # Relacionamento Espacial: ST_Within(equipamento, municipio)
    ax.annotate("", xy=(43.4, 70.0), xytext=(55.6, 70.0),
                arrowprops=dict(arrowstyle="<->", lw=1.3, ls="--", color="#0f766e"))
    ax.text(49.5, 70.0, "ST_Within\n(geom)", ha="center", va="center",
            fontsize=7.5, color="#0f766e",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f0fdfa", ec="#5eead4"))

    # Relacionamento FK: categoria_equipamento (1) -> equipamento_urbano (N)
    ax.annotate("", xy=(76.0, 56.5), xytext=(76.0, 42.6),
                arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#475569"))
    ax.text(76.0, 49.5, "FK 1:N (id_categoria)", ha="center", va="center",
            fontsize=7.8, color="#334155", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="#f8fafc", ec="#cbd5e1"))

    # Relacionamento Espacial: ST_Intersects(trecho_viario, municipio)
    ax.annotate("", xy=(23.5, 62.5), xytext=(23.5, 46.6),
                arrowprops=dict(arrowstyle="<->", lw=1.4, ls="--", color="#7c2d12"))
    ax.text(23.5, 54.5, "Espacial N:N\nST_Intersects(geom)", ha="center", va="center",
            fontsize=7.5, color="#7c2d12",
            bbox=dict(boxstyle="round,pad=0.25", fc="#fff7ed", ec="#fdba74"))

    # Relacionamento Espacial: ST_DWithin(equipamento, trecho_viario)
    ax.annotate("", xy=(43.4, 34.0), xytext=(55.6, 61.5),
                arrowprops=dict(arrowstyle="<->", lw=1.2, ls=":", color="#6b21a8",
                                connectionstyle="arc3,rad=-0.18"))
    ax.text(47.2, 46.5, "Proximidade\nST_DWithin(geography)", ha="center", va="center",
            fontsize=7.3, color="#6b21a8",
            bbox=dict(boxstyle="round,pad=0.25", fc="#faf5ff", ec="#d8b4fe"))

    ax.text(50, 97.5, "Diagrama Entidade-Relacionamento (DER) — Base infra_medio_piracicaba (SRID 4674)",
            ha="center", va="center", fontsize=12.5, fontweight="bold", color="#0f172a")

    plt.tight_layout(pad=0.4)
    plt.savefig(DOCS_DIR / "der.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("DER salvo em", DOCS_DIR / "der.png")


def gerar_mapa() -> None:
    muns = json.loads((PROC_DIR / "municipios.geojson").read_text(encoding="utf-8"))["features"]
    vias = json.loads((PROC_DIR / "trechos_viarios.geojson").read_text(encoding="utf-8"))["features"]
    eqs = json.loads((PROC_DIR / "equipamentos_urbanos.geojson").read_text(encoding="utf-8"))["features"]

    fig, ax = plt.subplots(figsize=(10.5, 9.5), dpi=250)
    ax.set_facecolor("#f8fafc")

    # 1. Polígonos dos municípios
    for f in muns:
        geom = shape(f["geometry"])
        reg = f["properties"]["regiao_imediata"]
        face = "#e0f2fe" if reg == "João Monlevade" else "#ecfdf5"
        for poly in geom.geoms:
            x, y = poly.exterior.xy
            ax.fill(x, y, facecolor=face, edgecolor="#64748b", linewidth=0.9, zorder=1)
        c = geom.centroid
        nome = f["properties"]["nome"]
        ax.text(c.x, c.y, nome, fontsize=6.5, ha="center", va="center",
                color="#1e293b", fontweight="semibold", zorder=4,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.65))

    # 2. Trechos viários por hierarquia
    style_via = {
        "TRUNK": ("#b91c1c", 1.8),
        "PRIMARY": ("#ea580c", 1.3),
        "SECONDARY": ("#d97706", 0.9),
        "TERTIARY": ("#94a3b8", 0.55),
    }
    for f in vias:
        classe = f["properties"]["classe_via"]
        color, lw = style_via.get(classe, ("#94a3b8", 0.5))
        geom = shape(f["geometry"])
        for line in geom.geoms:
            x, y = line.xy
            ax.plot(x, y, color=color, linewidth=lw, alpha=0.85, zorder=2)

    # 3. Equipamentos urbanos por categoria
    cat_style = {
        1: ("#dc2626", "o", "Saúde (36)"),
        2: ("#2563eb", "^", "Educação (73)"),
        3: ("#111827", "s", "Segurança/Justiça (19)"),
        4: ("#7c3aed", "D", "Transporte (11)"),
        5: ("#059669", "P", "Serviços Públicos (24)"),
    }
    for cat_id, (color, marker, _) in cat_style.items():
        pts = [shape(f["geometry"]) for f in eqs if f["properties"]["id_categoria"] == cat_id]
        if pts:
            ax.scatter([p.x for p in pts], [p.y for p in pts],
                       c=color, marker=marker, s=26, edgecolors="white",
                       linewidths=0.45, zorder=5)

    # Legenda
    handles = [
        mpatches.Patch(facecolor="#e0f2fe", edgecolor="#64748b", label="Região Imediata de João Monlevade (6 mun.)"),
        mpatches.Patch(facecolor="#ecfdf5", edgecolor="#64748b", label="Região Imediata de Itabira (9 mun.)"),
        Line2D([0], [0], color="#b91c1c", lw=2.0, label="Via Arterial / Tronco (TRUNK)"),
        Line2D([0], [0], color="#ea580c", lw=1.4, label="Via Primária (PRIMARY)"),
        Line2D([0], [0], color="#d97706", lw=1.0, label="Via Secundária (SECONDARY)"),
        Line2D([0], [0], color="#94a3b8", lw=0.7, label="Via Terciária (TERTIARY)"),
    ]
    for cat_id, (color, marker, label) in cat_style.items():
        handles.append(Line2D([0], [0], marker=marker, color="w", label=label,
                              markerfacecolor=color, markeredgecolor="white", markersize=7))

    ax.legend(handles=handles, loc="lower left", fontsize=7.5, frameon=True,
              facecolor="white", edgecolor="#cbd5e1", title="Legenda", title_fontsize=8.5)

    ax.set_title(
        "Infraestrutura Pública e Sistema Viário Regional\n"
        "Regiões Imediatas de João Monlevade e Itabira (MG) — SIRGAS 2000 (EPSG:4674)",
        fontsize=11.5, fontweight="bold", pad=10, color="#0f172a",
    )
    ax.set_xlabel("Longitude (°)", fontsize=9)
    ax.set_ylabel("Latitude (°)", fontsize=9)
    ax.grid(True, linestyle=":", alpha=0.45, color="#94a3b8")
    ax.set_aspect("equal")

    # Seta Norte simples
    ax.annotate("N", xy=(0.95, 0.94), xytext=(0.95, 0.87),
                xycoords="axes fraction", ha="center", va="center",
                fontsize=11, fontweight="bold", color="#0f172a",
                arrowprops=dict(facecolor="#0f172a", width=2.5, headwidth=8))

    plt.tight_layout()
    plt.savefig(DOCS_DIR / "mapa_recorte.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Mapa salvo em", DOCS_DIR / "mapa_recorte.png")


if __name__ == "__main__":
    gerar_der()
    gerar_mapa()
