#!/usr/bin/env python3
"""Trata, limpa, valida e padroniza os dados brutos do IBGE e do OpenStreetMap,
gerando os arquivos em dados/tratados/, o script sql/dados.sql e o log de tratamento.
"""

import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "dados" / "brutos"
PROC_DIR = BASE_DIR / "dados" / "tratados"
SQL_DIR = BASE_DIR / "sql"
SCRIPTS_DIR = BASE_DIR / "scripts"

PROC_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

# Transformador SIRGAS 2000 (4674) -> SIRGAS 2000 / UTM 23S (31983) para cálculos métricos
TO_UTM23S = Transformer.from_crs("EPSG:4674", "EPSG:31983", always_xy=True).transform

CATEGORIAS = [
    (1, "SAUDE", "Saúde", "Hospitais, clínicas, consultórios médicos e farmácias."),
    (2, "EDUCACAO", "Educação", "Escolas, creches, faculdades, universidades e bibliotecas."),
    (3, "SEGURANCA", "Segurança e Justiça", "Delegacias, quartéis de bombeiros e fóruns."),
    (4, "TRANSPORTE", "Transporte", "Terminais e estações rodoviárias."),
    (5, "SERVICO_PUBLICO", "Serviços Públicos e Comunitários", "Prefeituras, correios, bancos e assistência social."),
]

AMENITY_TO_CAT = {
    "hospital": (1, "Hospital"),
    "clinic": (1, "Clínica"),
    "doctors": (1, "Consultório médico"),
    "pharmacy": (1, "Farmácia"),
    "school": (2, "Escola"),
    "university": (2, "Universidade"),
    "college": (2, "Faculdade / Ensino técnico"),
    "kindergarten": (2, "Creche / Pré-escola"),
    "library": (2, "Biblioteca"),
    "police": (3, "Unidade policial"),
    "fire_station": (3, "Corpo de bombeiros"),
    "courthouse": (3, "Fórum / Tribunal"),
    "bus_station": (4, "Terminal rodoviário"),
    "townhall": (5, "Prefeitura"),
    "post_office": (5, "Agência dos Correios"),
    "bank": (5, "Agência bancária"),
    "social_facility": (5, "Equipamento de assistência social"),
}

PAVED_SURFACES = {
    "asphalt", "paved", "concrete", "concrete:plates", "cobblestone",
    "sett", "paving_stones", "chipseal",
}
UNPAVED_SURFACES = {
    "unpaved", "dirt", "earth", "gravel", "fine_gravel", "ground",
    "sand", "mud", "compacted", "grass",
}


def sql_str(val: str | None, max_len: int | None = None) -> str:
    if val is None:
        return "NULL"
    cleaned = " ".join(str(val).strip().split())
    if not cleaned:
        return "NULL"
    if max_len is not None:
        cleaned = cleaned[:max_len]
    return "'" + cleaned.replace("'", "''") + "'"


def ensure_multipolygon(geom) -> MultiPolygon:
    if not geom.is_valid:
        geom = make_valid(geom)
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    if isinstance(geom, MultiPolygon):
        return geom
    polys = [g for g in getattr(geom, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    flat = []
    for p in polys:
        if isinstance(p, Polygon):
            flat.append(p)
        else:
            flat.extend(p.geoms)
    return MultiPolygon(flat)


def ensure_multilinestring(geom) -> MultiLineString | None:
    if not geom.is_valid:
        geom = make_valid(geom)
    if isinstance(geom, LineString):
        return MultiLineString([geom]) if len(geom.coords) >= 2 else None
    if isinstance(geom, MultiLineString):
        lines = [l for l in geom.geoms if len(l.coords) >= 2]
        return MultiLineString(lines) if lines else None
    lines = [g for g in getattr(geom, "geoms", []) if isinstance(g, LineString) and len(g.coords) >= 2]
    return MultiLineString(lines) if lines else None


def main() -> None:
    logs: list[str] = []
    logs.append("=== LOG DE TRATAMENTO DOS DADOS ===")

    # 1. Municípios
    mun_raw = json.loads((RAW_DIR / "ibge_municipios_raw.geojson").read_text(encoding="utf-8"))
    municipios = []
    mun_geoms = []
    mun_corrigidos = 0

    for feat in mun_raw["features"]:
        props = feat["properties"]
        geom_orig = shape(feat["geometry"])
        if not geom_orig.is_valid:
            mun_corrigidos += 1
        geom = ensure_multipolygon(geom_orig)
        assert geom.is_valid and not geom.is_empty

        geom_utm = transform(TO_UTM23S, geom)
        area_km2 = round(geom_utm.area / 1_000_000.0, 3)

        reg = {
            "cod_ibge": int(props["cod_ibge"]),
            "nome": " ".join(props["nome"].split()),
            "uf": props["uf"],
            "regiao_imediata": props["regiao_imediata"],
            "area_km2": area_km2,
            "populacao_2022": props.get("populacao_2022"),
            "geom": geom,
        }
        municipios.append(reg)
        mun_geoms.append((reg["cod_ibge"], geom))

    area_recorte = unary_union([g for _, g in mun_geoms])
    logs.append(f"Municípios lidos: {len(mun_raw['features'])}; válidos finais: {len(municipios)}; geometrias corrigidas: {mun_corrigidos}.")

    # 2. Equipamentos urbanos
    eq_raw = json.loads((RAW_DIR / "osm_equipamentos_raw.json").read_text(encoding="utf-8"))
    equipamentos = []
    eq_fora_recorte = 0
    eq_sem_nome = 0
    eq_sem_coord = 0
    seen_eq_ids = set()

    for el in eq_raw.get("elements", []):
        osm_id = int(el["id"])
        if osm_id in seen_eq_ids:
            continue
        seen_eq_ids.add(osm_id)

        tags = el.get("tags", {})
        amenity = tags.get("amenity")
        if amenity not in AMENITY_TO_CAT:
            continue

        if "lon" in el and "lat" in el:
            lon, lat = float(el["lon"]), float(el["lat"])
        elif "center" in el:
            lon, lat = float(el["center"]["lon"]), float(el["center"]["lat"])
        else:
            eq_sem_coord += 1
            continue

        pt = Point(lon, lat)
        if not pt.is_valid or pt.is_empty:
            eq_sem_coord += 1
            continue

        cod_ibge_match = None
        for cid, mgeom in mun_geoms:
            if mgeom.contains(pt):
                cod_ibge_match = cid
                break

        if cod_ibge_match is None:
            eq_fora_recorte += 1
            continue

        id_cat, label_pt = AMENITY_TO_CAT[amenity]
        nome = tags.get("name")
        if not nome or not nome.strip():
            nome = f"{label_pt} sem nome (OSM {osm_id})"
            eq_sem_nome += 1

        bairro = tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:district")
        operador = tags.get("operator")

        equipamentos.append({
            "osm_id": osm_id,
            "nome": " ".join(nome.split())[:150],
            "tipo_osm": amenity,
            "id_categoria": id_cat,
            "cod_ibge": cod_ibge_match,
            "bairro_ou_localidade": " ".join(bairro.split())[:120] if bairro else None,
            "operador": " ".join(operador.split())[:120] if operador else None,
            "geom": pt,
        })

    logs.append(
        f"Equipamentos brutos: {len(eq_raw.get('elements', []))}; "
        f"mantidos no recorte: {len(equipamentos)}; "
        f"descartados fora dos 15 municípios: {eq_fora_recorte}; "
        f"sem coordenada: {eq_sem_coord}; "
        f"nomes padronizados (ausentes no OSM): {eq_sem_nome}."
    )

    # 3. Trechos viários
    vias_raw = json.loads((RAW_DIR / "osm_vias_raw.json").read_text(encoding="utf-8"))
    vias = []
    vias_fora = 0
    vias_invalidas = 0
    vias_corrigidas = 0
    seen_via_ids = set()

    for el in vias_raw.get("elements", []):
        if el.get("type") != "way":
            continue
        osm_id = int(el["id"])
        if osm_id in seen_via_ids:
            continue
        seen_via_ids.add(osm_id)

        coords = [(float(p["lon"]), float(p["lat"])) for p in el.get("geometry", [])]
        if len(coords) < 2:
            vias_invalidas += 1
            continue

        ls = LineString(coords)
        if not ls.is_valid:
            vias_corrigidas += 1
        mls = ensure_multilinestring(ls)
        if mls is None or not mls.is_valid or mls.is_empty:
            vias_invalidas += 1
            continue

        if not area_recorte.intersects(mls):
            vias_fora += 1
            continue

        tags = el.get("tags", {})
        highway = tags.get("highway", "").upper()
        if highway not in {"MOTORWAY", "TRUNK", "PRIMARY", "SECONDARY", "TERTIARY"}:
            continue

        surface = tags.get("surface", "").strip().lower()
        if surface in PAVED_SURFACES:
            pavimentado = True
        elif surface in UNPAVED_SURFACES:
            pavimentado = False
        else:
            pavimentado = None

        geom_utm = transform(TO_UTM23S, mls)
        extensao_km = round(geom_utm.length / 1000.0, 3)

        vias.append({
            "osm_id": osm_id,
            "codigo_rodovia": " ".join(tags["ref"].split())[:30] if tags.get("ref") else None,
            "nome": " ".join(tags["name"].split())[:150] if tags.get("name") else None,
            "classe_via": highway,
            "pavimentado": pavimentado,
            "extensao_km": extensao_km,
            "geom": mls,
        })

    logs.append(
        f"Trechos viários brutos: {len(vias_raw.get('elements', []))}; "
        f"mantidos no recorte: {len(vias)}; "
        f"descartados fora do recorte: {vias_fora}; "
        f"inválidos/descartados: {vias_invalidas}; "
        f"geometrias corrigidas: {vias_corrigidas}."
    )
    total_feicoes = len(municipios) + len(equipamentos) + len(vias)
    logs.append(f"Total de feições espaciais finais: {total_feicoes}.")

    # Salvar GeoJSONs tratados
    def write_geojson(path: Path, rows: list[dict]) -> None:
        fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4674"}},
            "features": [
                {
                    "type": "Feature",
                    "properties": {k: v for k, v in r.items() if k != "geom"},
                    "geometry": json.loads(json.dumps(r["geom"].__geo_interface__)),
                }
                for r in rows
            ],
        }
        path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    write_geojson(PROC_DIR / "municipios.geojson", municipios)
    write_geojson(PROC_DIR / "equipamentos_urbanos.geojson", equipamentos)
    write_geojson(PROC_DIR / "trechos_viarios.geojson", vias)

    # Gerar sql/dados.sql
    sql_lines = [
        "-- ============================================================================",
        "-- Carga de Dados: Infraestrutura Pública e Sistema Viário Regional (MG)",
        "-- SRID: 4674 (SIRGAS 2000)",
        "-- ============================================================================",
        "BEGIN;",
        "",
        "-- 1. Categorias de equipamentos (tabela de domínio)",
    ]
    for id_cat, cod, nome, desc in CATEGORIAS:
        sql_lines.append(
            f"INSERT INTO categoria_equipamento (id_categoria, codigo, nome, descricao) VALUES "
            f"({id_cat}, {sql_str(cod)}, {sql_str(nome)}, {sql_str(desc)});"
        )

    sql_lines.append("")
    sql_lines.append("-- 2. Municípios (15 feições)")
    for m in municipios:
        pop_sql = str(m["populacao_2022"]) if m["populacao_2022"] is not None else "NULL"
        wkt = m["geom"].wkt
        sql_lines.append(
            f"INSERT INTO municipio (cod_ibge, nome, uf, regiao_imediata, area_km2, populacao_2022, geom) VALUES "
            f"({m['cod_ibge']}, {sql_str(m['nome'], 100)}, {sql_str(m['uf'], 2)}, "
            f"{sql_str(m['regiao_imediata'], 60)}, {m['area_km2']:.3f}, {pop_sql}, "
            f"ST_GeomFromText('{wkt}', 4674));"
        )

    sql_lines.append("")
    sql_lines.append(f"-- 3. Equipamentos urbanos ({len(equipamentos)} feições)")
    for e in equipamentos:
        wkt = e["geom"].wkt
        sql_lines.append(
            f"INSERT INTO equipamento_urbano (osm_id, nome, tipo_osm, id_categoria, cod_ibge, bairro_ou_localidade, operador, geom) VALUES "
            f"({e['osm_id']}, {sql_str(e['nome'], 150)}, {sql_str(e['tipo_osm'], 50)}, "
            f"{e['id_categoria']}, {e['cod_ibge']}, {sql_str(e['bairro_ou_localidade'], 120)}, "
            f"{sql_str(e['operador'], 120)}, ST_GeomFromText('{wkt}', 4674));"
        )

    sql_lines.append("")
    sql_lines.append(f"-- 4. Trechos viários ({len(vias)} feições)")
    for v in vias:
        pav_sql = "TRUE" if v["pavimentado"] is True else ("FALSE" if v["pavimentado"] is False else "NULL")
        wkt = v["geom"].wkt
        sql_lines.append(
            f"INSERT INTO trecho_viario (osm_id, codigo_rodovia, nome, classe_via, pavimentado, extensao_km, geom) VALUES "
            f"({v['osm_id']}, {sql_str(v['codigo_rodovia'], 30)}, {sql_str(v['nome'], 150)}, "
            f"{sql_str(v['classe_via'], 30)}, {pav_sql}, {v['extensao_km']:.3f}, "
            f"ST_GeomFromText('{wkt}', 4674));"
        )

    sql_lines.append("")
    sql_lines.append("COMMIT;")
    (SQL_DIR / "dados.sql").write_text("\n".join(sql_lines) + "\n", encoding="utf-8")

    log_text = "\n".join(logs) + "\n"
    (SCRIPTS_DIR / "log_tratamento.txt").write_text(log_text, encoding="utf-8")
    print(log_text)


if __name__ == "__main__":
    main()
