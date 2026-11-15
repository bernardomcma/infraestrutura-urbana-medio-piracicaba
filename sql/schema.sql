-- ============================================================================
-- Base de Dados Geográficos: Infraestrutura Pública e Sistema Viário Regional
-- Recorte: Regiões Geográficas Imediatas de João Monlevade e Itabira (MG)
-- SRID: 4674 (SIRGAS 2000)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Limpeza idempotente para recriação em banco limpo ou de testes
DROP TABLE IF EXISTS equipamento_urbano CASCADE;
DROP TABLE IF EXISTS trecho_viario CASCADE;
DROP TABLE IF EXISTS categoria_equipamento CASCADE;
DROP TABLE IF EXISTS municipio CASCADE;

-- 1. Tabela de Municípios (Polígonos - IBGE)
CREATE TABLE municipio (
    cod_ibge        INTEGER PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    uf              CHAR(2) NOT NULL DEFAULT 'MG',
    regiao_imediata VARCHAR(60) NOT NULL,
    area_km2        NUMERIC(12, 3) NOT NULL,
    populacao_2022  INTEGER,
    geom            GEOMETRY(MultiPolygon, 4674) NOT NULL,
    CONSTRAINT chk_municipio_cod_ibge CHECK (cod_ibge BETWEEN 1000000 AND 9999999),
    CONSTRAINT chk_municipio_uf CHECK (uf = 'MG'),
    CONSTRAINT chk_municipio_area CHECK (area_km2 > 0),
    CONSTRAINT chk_municipio_pop CHECK (populacao_2022 IS NULL OR populacao_2022 >= 0),
    CONSTRAINT chk_municipio_geom_valida CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

-- 2. Tabela de Domínio: Categorias de Equipamentos Urbanos (sem geometria)
CREATE TABLE categoria_equipamento (
    id_categoria SMALLINT PRIMARY KEY,
    codigo       VARCHAR(30) NOT NULL UNIQUE,
    nome         VARCHAR(60) NOT NULL,
    descricao    VARCHAR(200) NOT NULL,
    CONSTRAINT chk_categoria_id CHECK (id_categoria > 0)
);

-- 3. Tabela de Equipamentos Urbanos e Serviços Públicos (Pontos - OSM)
CREATE TABLE equipamento_urbano (
    id_equipamento       SERIAL PRIMARY KEY,
    osm_id               BIGINT NOT NULL UNIQUE,
    nome                 VARCHAR(150) NOT NULL,
    tipo_osm             VARCHAR(50) NOT NULL,
    id_categoria         SMALLINT NOT NULL,
    cod_ibge             INTEGER NOT NULL,
    bairro_ou_localidade VARCHAR(120),
    operador             VARCHAR(120),
    geom                 GEOMETRY(Point, 4674) NOT NULL,
    CONSTRAINT fk_equipamento_categoria
        FOREIGN KEY (id_categoria) REFERENCES categoria_equipamento (id_categoria)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_equipamento_municipio
        FOREIGN KEY (cod_ibge) REFERENCES municipio (cod_ibge)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_equipamento_geom_valida CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

-- 4. Tabela de Trechos Viários e Rodoviários (Linhas - OSM)
CREATE TABLE trecho_viario (
    id_trecho      SERIAL PRIMARY KEY,
    osm_id         BIGINT NOT NULL UNIQUE,
    codigo_rodovia VARCHAR(30),
    nome           VARCHAR(150),
    classe_via     VARCHAR(30) NOT NULL,
    pavimentado    BOOLEAN,
    extensao_km    NUMERIC(10, 3) NOT NULL,
    geom           GEOMETRY(MultiLineString, 4674) NOT NULL,
    CONSTRAINT chk_trecho_classe CHECK (
        classe_via IN ('MOTORWAY', 'TRUNK', 'PRIMARY', 'SECONDARY', 'TERTIARY')
    ),
    CONSTRAINT chk_trecho_extensao CHECK (extensao_km >= 0),
    CONSTRAINT chk_trecho_geom_valida CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom))
);

-- Índices Espaciais (GiST)
CREATE INDEX idx_municipio_geom ON municipio USING GIST (geom);
CREATE INDEX idx_equipamento_geom ON equipamento_urbano USING GIST (geom);
CREATE INDEX idx_trecho_geom ON trecho_viario USING GIST (geom);

-- Índices Auxiliares para Chaves Estrangeiras e Filtros Frequentes
CREATE INDEX idx_equipamento_cod_ibge ON equipamento_urbano (cod_ibge);
CREATE INDEX idx_equipamento_id_categoria ON equipamento_urbano (id_categoria);
CREATE INDEX idx_trecho_classe_via ON trecho_viario (classe_via);
