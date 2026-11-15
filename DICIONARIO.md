# Dicionário de Dados — Infraestrutura Pública e Sistema Viário Regional (Médio Piracicaba / MG)

**Autores:** Bernardo Martins da Costa Silva (24.1.8110) e Túlio de Paula Santos Dias (25.2.8031)  
**Disciplina:** CSI803 — Banco de Dados Geográficos (UFOP / ICEA / DECSI)

---

## 1. Visão Geral da Base

| Item | Descrição |
| :--- | :--- |
| **Título** | Infraestrutura Pública e Sistema Viário Regional: Regiões Imediatas de João Monlevade e Itabira (`infra_medio_piracicaba`) |
| **Descrição e finalidade** | Base de dados geográficos vetoriais contendo os limites oficiais dos 15 municípios das Regiões Geográficas Imediatas de João Monlevade e Itabira (MG), a rede viária principal (rodovias federais, estaduais e vias arteriais/coletoras) e os equipamentos urbanos e serviços públicos georreferenciados. Finalidade: apoiar análises espaciais de acessibilidade, cobertura territorial de serviços públicos e conectividade viária regional no PostGIS. |
| **Fontes** | **Municípios e população:** IBGE — API de Malhas Territoriais v3, API de Localidades v1 e API de Agregados (Censo Demográfico 2022, Agregado 4709, Variável 93), disponíveis em `servicodados.ibge.gov.br` / `ibge.gov.br/geociencias`.<br>**Rede viária e equipamentos urbanos:** OpenStreetMap (OSM), coletados via Overpass API (`overpass-api.de` / `lz4.overpass-api.de`). |
| **Data de coleta** | 15/11/2026 (todas as fontes). |
| **Licença** | **IBGE:** Dados abertos governamentais (Decreto nº 8.777/2016), com atribuição obrigatória ("Fonte: IBGE").<br>**OpenStreetMap:** Open Database License (ODbL 1.0), com atribuição obrigatória ("© OpenStreetMap contributors") e compartilhamento pela mesma licença.<br>**Código e documentação:** MIT License (ver arquivo `LICENSE`). |
| **Cobertura espacial** | 15 municípios de Minas Gerais: 6 da Região Geográfica Imediata de João Monlevade (Bela Vista de Minas, João Monlevade, Nova Era, Rio Piracicaba, São Domingos do Prata, São Gonçalo do Rio Abaixo) e 9 da Região Geográfica Imediata de Itabira (Bom Jesus do Amparo, Carmésia, Ferros, Itabira, Itambé do Mato Dentro, Passabém, Santa Maria de Itabira, Santo Antônio do Rio Abaixo, São Sebastião do Rio Preto). Área total aproximada: 6.099,38 km². |
| **Cobertura temporal** | Malha territorial vigente e população do Censo Demográfico 2022 (IBGE); retrato colaborativo do OpenStreetMap vigente em 15/11/2026. Não há série histórica. |
| **SRID e justificativa** | **EPSG:4674 (SIRGAS 2000).** É o Sistema Geodésico de Referência oficial do Brasil e o datum padrão das malhas do IBGE, evitando distorções de transformação nos limites municipais. Para cálculos métricos de área e extensão no tratamento e nas consultas, as geometrias são convertidas para `geography` no PostGIS ou reprojetadas para **EPSG:31983 (SIRGAS 2000 / UTM zona 23S)**. |
| **Escala e precisão** | Malha municipal do IBGE em qualidade intermediária (escala de referência regional 1:250.000). Feições do OpenStreetMap possuem precisão posicional variável (tipicamente de alguns metros a dezenas de metros, conforme vetorização por imagem de satélite ou GPS colaborativo). |
| **Tratamentos aplicados** | 1. Coleta automatizada via `scripts/coletar_dados.py` com registro dos arquivos originais em `dados/brutos/`.<br>2. Validação geométrica e conversão explícita para tipos `MultiPolygon`, `MultiLineString` e `Point` (`scripts/tratar_dados.py`).<br>3. Cálculo de `area_km2` e `extensao_km` em `EPSG:31983` (SIRGAS 2000 / UTM 23S).<br>4. Filtragem espacial: descarte de 93 equipamentos e 1.025 trechos viários capturados no *bounding box* que não pertenciam nem intersectavam os 15 municípios.<br>5. Atribuição da chave estrangeira `cod_ibge` aos equipamentos por relação espacial `contains`/`within` contra `municipio`.<br>6. Padronização de 38 equipamentos sem tag `name` no OSM para `"<Tipo> sem nome (OSM <id>)"`, padronização de textos em UTF-8 sem espaços redundantes e nomes de colunas em `snake_case`. |

---

## 2. Descrição das Tabelas

### Tabela `municipio`
Limites territoriais oficiais e dados demográficos dos municípios do recorte.  
**Geometria:** `MultiPolygon` · **SRID:** `4674` · **Registros:** `15`

| Coluna | Tipo | Tam. / Domínio | Nulo? | PK / FK | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cod_ibge` | `integer` | 7 dígitos (1000000–9999999) | Não | PK | Código oficial do município no IBGE. | `3136207` |
| `nome` | `varchar` | 100 | Não | — | Nome oficial do município em UTF-8. | `João Monlevade` |
| `uf` | `char` | 2 · `'MG'` | Não | — | Sigla da unidade da federação. | `MG` |
| `regiao_imediata` | `varchar` | 60 | Não | — | Nome da Região Geográfica Imediata (IBGE). | `João Monlevade` |
| `area_km2` | `numeric` | (12,3) · > 0 | Não | — | Área territorial em km², calculada em EPSG:31983. | `98.519` |
| `populacao_2022` | `integer` | ≥ 0 | Sim | — | População residente segundo o Censo Demográfico 2022 (IBGE). | `80187` |
| `geom` | `geometry` | `MultiPolygon, 4674` | Não | — | Geometria do limite municipal (válida e não vazia). | `MULTIPOLYGON(((-43.17 ...)))` |

---

### Tabela `categoria_equipamento` (tabela de domínio)
Classificação temática dos equipamentos urbanos e serviços públicos.  
**Geometria:** Sem geometria · **Registros:** `5`

| Coluna | Tipo | Tam. / Domínio | Nulo? | PK / FK | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `id_categoria` | `smallint` | 1 a 5 (> 0) | Não | PK | Identificador numérico interno da categoria. | `1` |
| `codigo` | `varchar` | 30 · único | Não | — | Código textual padronizado em maiúsculas. | `SAUDE` |
| `nome` | `varchar` | 60 | Não | — | Nome legível da categoria. | `Saúde` |
| `descricao` | `varchar` | 200 | Não | — | Descrição dos tipos de equipamentos abrangidos. | `Hospitais, clínicas, consultórios médicos e farmácias.` |

---

### Tabela `equipamento_urbano`
Equipamentos públicos, comunitários e serviços essenciais localizados nos 15 municípios.  
**Geometria:** `Point` · **SRID:** `4674` · **Registros:** `163`

| Coluna | Tipo | Tam. / Domínio | Nulo? | PK / FK | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `id_equipamento` | `serial` | gerado (> 0) | Não | PK | Identificador sequencial interno do equipamento. | `1` |
| `osm_id` | `bigint` | único | Não | — | Identificador original do elemento no OpenStreetMap. | `1495738201` |
| `nome` | `varchar` | 150 | Não | — | Nome do equipamento (ou rótulo padronizado quando ausente no OSM). | `Hospital Margarida` |
| `tipo_osm` | `varchar` | 50 · ver seção 4 | Não | — | Valor da etiqueta `amenity` no OpenStreetMap. | `hospital` |
| `id_categoria` | `smallint` | ver `categoria_equipamento` | Não | FK | Categoria temática do equipamento. Referencia `categoria_equipamento.id_categoria`. | `1` |
| `cod_ibge` | `integer` | 7 dígitos | Não | FK | Município onde o ponto está contido. Referencia `municipio.cod_ibge`. | `3136207` |
| `bairro_ou_localidade` | `varchar` | 120 | Sim | — | Bairro, distrito ou localidade (`addr:suburb` / `addr:neighbourhood`), quando informado. | `Carneirinhos` |
| `operador` | `varchar` | 120 | Sim | — | Órgão ou instituição mantenedora (`operator`), quando informado. | `Prefeitura Municipal` |
| `geom` | `geometry` | `Point, 4674` | Não | — | Coordenada geográfica do equipamento (ou centroide de edificação no OSM). | `POINT(-43.1735 -19.8112)` |

---

### Tabela `trecho_viario`
Trechos de rodovias federais, estaduais e vias estruturantes principais que cortam o recorte.  
**Geometria:** `MultiLineString` · **SRID:** `4674` · **Registros:** `2.001`

| Coluna | Tipo | Tam. / Domínio | Nulo? | PK / FK | Descrição | Exemplo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `id_trecho` | `serial` | gerado (> 0) | Não | PK | Identificador sequencial interno do trecho viário. | `1` |
| `osm_id` | `bigint` | único | Não | — | Identificador original do `way` no OpenStreetMap. | `28471930` |
| `codigo_rodovia` | `varchar` | 30 | Sim | — | Sigla/código oficial da rodovia (`ref`), quando presente. | `BR-381` |
| `nome` | `varchar` | 150 | Sim | — | Nome da via ou rodovia (`name`), quando informado no OSM. | `Avenida Getúlio Vargas` |
| `classe_via` | `varchar` | 30 · ver seção 4 | Não | — | Classificação hierárquica da via (`highway` em maiúsculas). | `TRUNK` |
| `pavimentado` | `boolean` | `TRUE` / `FALSE` / `NULL` | Sim | — | Indica se o trecho é pavimentado, derivado da etiqueta `surface` do OSM (`NULL` quando não mapeado). | `TRUE` |
| `extensao_km` | `numeric` | (10,3) · ≥ 0 | Não | — | Extensão do trecho em quilômetros, calculada em EPSG:31983. | `1.425` |
| `geom` | `geometry` | `MultiLineString, 4674` | Não | — | Traçado geométrico do trecho viário. | `MULTILINESTRING((-43.18 -19.82, ...))` |

---

## 3. Relacionamentos

| Origem | Destino | Tipo | Descrição |
| :--- | :--- | :--- | :--- |
| `equipamento_urbano.cod_ibge` | `municipio.cod_ibge` | FK 1:N | Cada equipamento pertence a exatamente um município do recorte. |
| `equipamento_urbano.id_categoria` | `categoria_equipamento.id_categoria` | FK 1:N | Cada equipamento é classificado em uma categoria temática. |
| `equipamento_urbano.geom` | `municipio.geom` | Espacial 1:N | `ST_Within(equipamento_urbano.geom, municipio.geom)`: garante coerência entre a localização e o `cod_ibge` atribuído. |
| `trecho_viario.geom` | `municipio.geom` | Espacial N:N | `ST_Intersects(trecho_viario.geom, municipio.geom)`: um trecho viário pode atravessar divisas municipais. |
| `equipamento_urbano.geom` | `trecho_viario.geom` | Espacial (proximidade) | `ST_DWithin(e.geom::geography, t.geom::geography, 500)`: identifica equipamentos a até 500 m de rodovias principais. |

---

## 4. Domínios e Códigos

| Coluna | Valor | Significado |
| :--- | :--- | :--- |
| `categoria_equipamento.id_categoria` | `1` (`SAUDE`) | Saúde: `hospital`, `clinic`, `doctors`, `pharmacy`. |
| | `2` (`EDUCACAO`) | Educação: `school`, `university`, `college`, `kindergarten`, `library`. |
| | `3` (`SEGURANCA`) | Segurança e Justiça: `police`, `fire_station`, `courthouse`. |
| | `4` (`TRANSPORTE`) | Transporte: `bus_station`. |
| | `5` (`SERVICO_PUBLICO`) | Serviços Públicos e Comunitários: `townhall`, `post_office`, `bank`, `social_facility`. |
| `trecho_viario.classe_via` | `TRUNK` | Rodovia ou via arterial tronco (ex.: BR-381, BR-262). |
| | `PRIMARY` | Rodovia primária de ligação regional (ex.: MG-129, MG-434). |
| | `SECONDARY` | Rodovia ou via arterial secundária. |
| | `TERTIARY` | Via coletora ou vicinal principal. |
| | `MOTORWAY` | Autoestrada com controle total de acesso (prevista no domínio `CHECK`; 0 ocorrências no recorte atual). |
| `trecho_viario.pavimentado` | `TRUE` | Superfície pavimentada (`asphalt`, `paved`, `concrete`, `cobblestone`, `paving_stones`, etc.). |
| | `FALSE` | Superfície não pavimentada (`unpaved`, `dirt`, `gravel`, `ground`, `compacted`, etc.). |
| | `NULL` | Tipo de superfície não informado no OpenStreetMap. |

---

## 5. Qualidade e Limitações

- **Completude colaborativa (OpenStreetMap):** Por ser uma base colaborativa, áreas rurais e municípios menores (como Passabém, Carmésia e São Sebastião do Rio Preto) apresentam menor densidade de mapeamento de equipamentos urbanos do que polos regionais como Itabira e João Monlevade.
- **Atributos nulos e nomes ausentes:**
  - `equipamento_urbano`: 38 dos 163 equipamentos (23,3%) não possuíam etiqueta `name` no OSM e receberam rótulo padronizado; `bairro_ou_localidade` é nulo em 92 registros (56,4%) e `operador` em 154 registros (94,5%).
  - `trecho_viario`: `codigo_rodovia` é nulo em 1.142 dos 2.001 trechos (57,1%, típico de vias urbanas), `nome` é nulo em 921 trechos (46,0%) e `pavimentado` é nulo em 425 trechos (21,2%).
- **Escala e uso recomendado:** A base é adequada para análises regionais, municipais e de acessibilidade viária. Não deve ser utilizada para fins cadastrais de lotes ou demarcação legal de divisas.
- **Reprodutibilidade:** Todo o processo de coleta e tratamento está versionado em `scripts/coletar_dados.py` e `scripts/tratar_dados.py`, com registro de execução em `scripts/log_tratamento.txt`.
