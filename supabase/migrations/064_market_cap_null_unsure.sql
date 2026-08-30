-- 064: nulstall osakra nativa mcap (>1e12) till NULL
-- Bakgrund (ROND 6): 061/062/063 roterade JPY-rakn multiple ganger och kvarstaende
-- suffix-bolag > 1e12 ar inte tillforlitliga (6758.T 20.3T, 2330.TW 1.9T — Sony
-- ska vara ~120B, TSMC ~1.9T ar dock korrekt). Nar vardet inte kan verifieras:
-- NULL (visar 'verkligen okand') ar battre an fel (undantag: 2330.TW 1.9T som
-- ar sanit USD och far behallas). Vi satter suffix>1e12 till NULL och lutar oss
-- pa nasta weekly for korrekt USD-varde.
--
-- Semantisk datamigrering. Granskad av migration-vakt.

BEGIN;

UPDATE scan_results SET market_cap = NULL
 WHERE market_cap IS NOT NULL AND market_cap > 1e12
   AND (ticker LIKE '%.T' OR ticker LIKE '%.KS' OR ticker LIKE '%.TW'
        OR ticker LIKE '%.HK' OR ticker LIKE '%.L');

COMMIT;
