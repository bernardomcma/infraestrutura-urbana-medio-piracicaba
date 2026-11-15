-- ============================================================================
-- Consultas Espaciais de Exemplo e Validação
-- Base: Infraestrutura Pública e Sistema Viário Regional (MG)
-- ============================================================================

-- 1. Validação de integridade geométrica (todas devem retornar 0 inválidas/vazias)
SELECT 'municipio' AS tabela,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom)) AS invalidas
FROM municipio
UNION ALL
SELECT 'equipamento_urbano',
       COUNT(*),
       COUNT(*) FILTER (WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom))
FROM equipamento_urbano
UNION ALL
SELECT 'trecho_viario',
       COUNT(*),
       COUNT(*) FILTER (WHERE NOT ST_IsValid(geom) OR ST_IsEmpty(geom))
FROM trecho_viario;

-- 2. Conferência da consistência espacial entre FK cod_ibge e ST_Within
SELECT e.id_equipamento, e.nome, e.cod_ibge AS fk_municipio, m.cod_ibge AS geom_municipio
FROM equipamento_urbano e
JOIN municipio m ON ST_Within(e.geom, m.geom)
WHERE e.cod_ibge <> m.cod_ibge;

-- 3. Quantidade de equipamentos urbanos por município e taxa por 10 mil habitantes
SELECT m.cod_ibge,
       m.nome AS municipio,
       m.regiao_imediata,
       m.populacao_2022,
       COUNT(e.id_equipamento) AS total_equipamentos,
       ROUND(
           (COUNT(e.id_equipamento)::NUMERIC / NULLIF(m.populacao_2022, 0)) * 10000,
           2
       ) AS equipamentos_por_10mil_hab
FROM municipio m
LEFT JOIN equipamento_urbano e ON e.cod_ibge = m.cod_ibge
GROUP BY m.cod_ibge, m.nome, m.regiao_imediata, m.populacao_2022
ORDER BY total_equipamentos DESC, m.nome;

-- 4. Distribuição de equipamentos por categoria e município
SELECT m.nome AS municipio,
       c.nome AS categoria,
       COUNT(e.id_equipamento) AS quantidade
FROM municipio m
JOIN equipamento_urbano e ON e.cod_ibge = m.cod_ibge
JOIN categoria_equipamento c ON c.id_categoria = e.id_categoria
GROUP BY m.nome, c.nome
ORDER BY m.nome, quantidade DESC;

-- 5. Extensão viária total (km) por município usando interseção espacial
SELECT m.nome AS municipio,
       COUNT(DISTINCT t.id_trecho) AS qtd_trechos,
       ROUND(
           SUM(ST_Length(ST_Intersection(t.geom, m.geom)::geography) / 1000.0)::NUMERIC,
           2
       ) AS extensao_no_municipio_km
FROM municipio m
JOIN trecho_viario t ON ST_Intersects(t.geom, m.geom)
GROUP BY m.nome
ORDER BY extensao_no_municipio_km DESC;

-- 6. Equipamentos de saúde localizados a até 500 metros de rodovias federais/estaduais (trunk/primary)
SELECT DISTINCT
       e.id_equipamento,
       e.nome AS equipamento,
       e.tipo_osm,
       m.nome AS municipio,
       t.codigo_rodovia,
       ROUND(ST_Distance(e.geom::geography, t.geom::geography)::NUMERIC, 1) AS distancia_m
FROM equipamento_urbano e
JOIN categoria_equipamento c ON c.id_categoria = e.id_categoria
JOIN municipio m ON m.cod_ibge = e.cod_ibge
JOIN trecho_viario t ON ST_DWithin(e.geom::geography, t.geom::geography, 500)
WHERE c.codigo = 'SAUDE'
  AND t.classe_via IN ('MOTORWAY', 'TRUNK', 'PRIMARY')
ORDER BY distancia_m ASC, e.nome;
