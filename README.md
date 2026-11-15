# Infraestrutura Pública e Sistema Viário Regional — Médio Piracicaba (MG)

Base de dados geográficos modelada para **PostgreSQL / PostGIS**, reunindo os limites municipais oficiais, a rede viária principal e os equipamentos urbanos e serviços públicos dos **15 municípios** das Regiões Geográficas Imediatas de **João Monlevade** e **Itabira** (Minas Gerais).

Trabalho desenvolvido para a disciplina **CSI803 — Banco de Dados Geográficos** (Universidade Federal de Ouro Preto — UFOP / ICEA / DECSI).

**Participantes:**
- **Bernardo Martins da Costa Silva** — Matrícula: `24.1.8110`
- **Túlio de Paula Santos Dias** — Matrícula: `25.2.8031`

---

## Resumo da Base

| Tabela | Tipo | Geometria / SRID | Registros | Fonte |
| :--- | :--- | :--- | :---: | :--- |
| `municipio` | Espacial | `MultiPolygon` (`EPSG:4674`) | 15 | IBGE (Malhas v3 + Censo 2022) |
| `categoria_equipamento` | Domínio | Sem geometria | 5 | Domínio interno |
| `equipamento_urbano` | Espacial | `Point` (`EPSG:4674`) | 163 | OpenStreetMap (Overpass API) |
| `trecho_viario` | Espacial | `MultiLineString` (`EPSG:4674`) | 2.001 | OpenStreetMap (Overpass API) |
| **Total de feições espaciais** | — | — | **2.179** | — |

Para detalhes completos de colunas, domínios, relacionamentos e limitações, consulte o [DICIONARIO.md](DICIONARIO.md) e o relatório completo em LaTeX/ABNT em `docs/relatorio_abnt.pdf`.

---

## Fontes e Licenças

1. **IBGE — Instituto Brasileiro de Geografia e Estatística**
   - *Localidades, Malhas Territoriais v3 (qualidade intermediária) e Agregados (Censo Demográfico 2022, Agregado 4709 / Variável 93).*
   - URL: <https://servicodados.ibge.gov.br/api/docs> e <https://www.ibge.gov.br/geociencias>
   - Data de coleta: `15/11/2026`
   - Licença: Dados abertos governamentais (Decreto nº 8.777/2016) — atribuição obrigatória ("Fonte: IBGE").

2. **OpenStreetMap (via Overpass API)**
   - *Vias principais (`highway` in `motorway|trunk|primary|secondary|tertiary`) e equipamentos urbanos (`amenity`).*
   - URL: <https://www.openstreetmap.org> / <https://overpass-api.de>
   - Data de coleta: `15/11/2026`
   - Licença: **Open Database License (ODbL 1.0)** — atribuição obrigatória ("© OpenStreetMap contributors").

3. **Código e Documentação**
   - Licença: **MIT** (consulte o arquivo [LICENSE](LICENSE)).

---

## Estrutura do Repositório

```text
infraestrutura-urbana-medio-piracicaba/
├── README.md                  # Descrição, fontes, requisitos e guia de importação
├── DICIONARIO.md              # Dicionário de dados completo
├── LICENSE                    # Licenças do código (MIT) e dos dados (IBGE / ODbL 1.0)
├── sql/
│   ├── schema.sql             # Extensão PostGIS, tabelas, PK/FK, CHECKs e índices GiST
│   ├── dados.sql              # Carga completa em UTF-8 (2.179 feições espaciais + 5 domínios)
│   └── consultas.sql          # Consultas espaciais de validação e análise regional
├── dados/
│   ├── brutos/                # Dados originais coletados das APIs (GeoJSON e JSON)
│   └── tratados/              # Camadas tratadas e padronizadas em GeoJSON (EPSG:4674)
├── scripts/
│   ├── coletar_dados.py       # Coleta reproduzível via IBGE API e Overpass API
│   ├── tratar_dados.py        # Limpeza, filtragem espacial, validação e geração de dados.sql
│   ├── gerar_figuras.py       # Geração do DER e do mapa cartográfico do recorte
│   └── log_tratamento.txt     # Registro quantitativo das etapas de tratamento
└── docs/
    ├── der.png                # Diagrama Entidade-Relacionamento
    ├── mapa_recorte.png       # Mapa do recorte espacial
    ├── relatorio_abnt.tex     # Relatório técnico em LaTeX (normas ABNT / abnTeX2)
    └── relatorio_abnt.pdf     # Relatório compilado em PDF
```

---

## Requisitos

- **PostgreSQL** `15+` (testado em banco limpo com **PostgreSQL 16** e **PostGIS 3.4** via imagem `postgis/postgis:16-3.4`)
- **PostGIS** `3.3+`
- *(Opcional, para reexecutar coleta/tratamento)* **Python** `3.11+` com `shapely`, `pyproj`, `matplotlib` e `pillow`.

---

## Como Importar no PostGIS (Banco Limpo)

### Opção 1: PostgreSQL + PostGIS local (`psql`)

```bash
# 1. Criar um banco limpo com codificação UTF-8
createdb -U postgres -E UTF8 infra_medio_piracicaba

# 2. Criar extensão PostGIS, tabelas, restrições e índices GiST
psql -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/schema.sql

# 3. Importar todas as feições e registros de domínio
psql -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/dados.sql

# 4. (Opcional) Executar as consultas espaciais de validação e análise
psql -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/consultas.sql
```

### Opção 2: Banco limpo com Docker (`postgis/postgis:16-3.4`)

```bash
docker run --name postgis-bdg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=infra_medio_piracicaba -p 5432:5432 -d postgis/postgis:16-3.4

# Aguarde ~5 segundos e execute os scripts a partir da raiz do repositório:
psql -h localhost -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/schema.sql
psql -h localhost -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/dados.sql
psql -h localhost -U postgres -d infra_medio_piracicaba -v ON_ERROR_STOP=1 -f sql/consultas.sql
```

---

## Como Citar esta Base

> SILVA, Bernardo Martins da Costa; DIAS, Túlio de Paula Santos. **Infraestrutura Pública e Sistema Viário Regional: Regiões Imediatas de João Monlevade e Itabira (MG)**. Ouro Preto / João Monlevade: UFOP, 2026. Base de dados geográficos em PostGIS (EPSG:4674). Fontes: IBGE (2022/2026) e © OpenStreetMap contributors (ODbL 1.0).
