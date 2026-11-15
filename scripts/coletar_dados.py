#!/usr/bin/env python3
"""Coleta dados brutos do IBGE (malhas e população Censo 2022) e do OpenStreetMap (Overpass API)
para as Regiões Geográficas Imediatas de João Monlevade e Itabira (MG).
"""

import gzip
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "dados" / "brutos"
RAW_DIR.mkdir(parents=True, exist_ok=True)

REGIOES_IMEDIATAS = {310026: "João Monlevade", 310005: "Itabira"}
HEADERS = {"User-Agent": "UFOP-CSI803-BDG-Coleta/1.0"}


def fetch_json(url: str, data: bytes | None = None, timeout: int = 60) -> dict | list:
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def coletar_municipios() -> list[dict]:
    print("1. Coletando lista de municípios de MG no IBGE...")
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/MG/municipios"
    todos = fetch_json(url)
    selecionados = [
        {
            "cod_ibge": int(m["id"]),
            "nome": m["nome"],
            "uf": "MG",
            "regiao_imediata": REGIOES_IMEDIATAS[m["regiao-imediata"]["id"]],
        }
        for m in todos
        if m["regiao-imediata"]["id"] in REGIOES_IMEDIATAS
    ]
    selecionados.sort(key=lambda x: x["cod_ibge"])
    print(f"   -> {len(selecionados)} municípios selecionados.")

    # População Censo 2022 (Agregado 4709, variável 93)
    print("2. Coletando população do Censo 2022 (IBGE Agregados)...")
    cods = ",".join(str(m["cod_ibge"]) for m in selecionados)
    pop_url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/"
        f"variaveis/93?localidades=N6[{cods}]"
    )
    pop_data = fetch_json(pop_url)
    pop_map = {}
    for serie in pop_data[0]["resultados"][0]["series"]:
        cid = int(serie["localidade"]["id"])
        val = serie["serie"].get("2022")
        pop_map[cid] = int(val) if val and val.isdigit() else None

    # Malha territorial GeoJSON por município
    print("3. Coletando malhas municipais (GeoJSON) no IBGE...")
    features = []
    for m in selecionados:
        cid = m["cod_ibge"]
        m["populacao_2022"] = pop_map.get(cid)
        malha_url = (
            f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cid}"
            f"?formato=application/vnd.geo+json&qualidade=intermediaria"
        )
        gj = fetch_json(malha_url)
        feat = gj["features"][0]
        feat["properties"] = m
        features.append(feat)
        time.sleep(0.15)

    fc = {"type": "FeatureCollection", "features": features}
    out_path = RAW_DIR / "ibge_municipios_raw.geojson"
    out_path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"   -> Salvo em {out_path}")
    return features


def calcular_bbox(features: list[dict]) -> tuple[float, float, float, float]:
    min_lon, min_lat = 180.0, 90.0
    max_lon, max_lat = -180.0, -90.0

    def walk(coords):
        nonlocal min_lon, min_lat, max_lon, max_lat
        if isinstance(coords[0], (int, float)):
            lon, lat = coords[0], coords[1]
            min_lon = min(min_lon, lon)
            max_lon = max(max_lon, lon)
            min_lat = min(min_lat, lat)
            max_lat = max(max_lat, lat)
        else:
            for c in coords:
                walk(c)

    for f in features:
        walk(f["geometry"]["coordinates"])
    return (min_lat, min_lon, max_lat, max_lon)


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def fetch_overpass(query: str) -> dict:
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(2):
            try:
                print(f"   Consultando {endpoint} (tentativa {attempt + 1})...")
                return fetch_json(endpoint, data=payload, timeout=120)
            except Exception as err:
                last_err = err
                print(f"   Aviso: falha em {endpoint}: {err}")
                time.sleep(3)
    raise RuntimeError(f"Falha em todos os endpoints Overpass: {last_err}")


def coletar_overpass(bbox: tuple[float, float, float, float]) -> None:
    south, west, north, east = bbox
    bbox_str = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"

    # 1) Trechos viários principais
    print(f"4. Coletando trechos viários no OpenStreetMap (bbox={bbox_str})...")
    q_vias = f"""
    [out:json][timeout:90];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bbox_str});
    );
    out body geom;
    """
    data_vias = fetch_overpass(q_vias)
    out_vias = RAW_DIR / "osm_vias_raw.json"
    out_vias.write_text(json.dumps(data_vias, ensure_ascii=False), encoding="utf-8")
    print(f"   -> {len(data_vias.get('elements', []))} trechos viários brutos salvos em {out_vias}")

    time.sleep(2)

    # 2) Equipamentos urbanos / serviços públicos
    print("5. Coletando equipamentos públicos/comunitários no OpenStreetMap...")
    q_eq = f"""
    [out:json][timeout:90];
    (
      nwr["amenity"~"^(hospital|clinic|doctors|pharmacy|school|university|college|kindergarten|police|fire_station|townhall|post_office|bus_station|bank|courthouse|library|social_facility)$"]({bbox_str});
    );
    out center;
    """
    data_eq = fetch_overpass(q_eq)
    out_eq = RAW_DIR / "osm_equipamentos_raw.json"
    out_eq.write_text(json.dumps(data_eq, ensure_ascii=False), encoding="utf-8")
    print(f"   -> {len(data_eq.get('elements', []))} equipamentos brutos salvos em {out_eq}")


if __name__ == "__main__":
    feats = coletar_municipios()
    bbox = calcular_bbox(feats)
    coletar_overpass(bbox)
    print("Coleta concluída com sucesso!")
