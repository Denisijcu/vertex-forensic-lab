"""
Consulta única de resumen por sesión: la usan el HUD (telemetry_api) y el acta (main.export).

- cadence_ms: mediana de Δt dentro de ráfagas (igual que el perito).
- Bloqueo: el de la propia huella o, si no tiene, el de su IP cuando hay una regla real en netsh
  (un bloqueo por IP alcanza a todas las sesiones de esa IP).
"""
from lab_env import BURST_GAP_MS

SESSION_SUMMARY_SQL = f"""
WITH ip_block AS (
    SELECT ip_address,
           MAX(rule_name) AS rule_name,
           MAX(enforcement_status) AS enforcement_status
    FROM soar_actions
    WHERE enforcement_status IN ('ENFORCED_NETSH', 'ALREADY_ENFORCED')
    GROUP BY ip_address
)
SELECT
    e.session_fingerprint,                                                        -- 0
    e.client_ip,                                                                  -- 1
    MAX(e.user_agent) AS ua,                                                      -- 2
    COUNT(e.event_id) AS total_requests,                                          -- 3
    ROUND(COALESCE(MEDIAN(e.delta_t_ms)
          FILTER (WHERE e.delta_t_ms > 0 AND e.delta_t_ms <= {BURST_GAP_MS}), 0), 2) AS cadence_ms,  -- 4
    ROUND(MAX(e.payload_entropy), 3) AS max_entropy,                              -- 5
    STRING_AGG(DISTINCT e.deception_triggered, ', ') AS tags,                     -- 6
    COALESCE(v.classification, 'PENDING_AUTOPSY') AS classification,              -- 7
    COALESCE(v.confidence, 0.0) AS confidence,                                    -- 8
    COALESCE(v.verdict_json, '{{}}') AS verdict_json,                             -- 9
    COALESCE(s.rule_name, ib.rule_name, '') AS firewall_rule,                     -- 10
    COALESCE(s.enforcement_status, ib.enforcement_status, '') AS enforcement_status  -- 11
FROM forensic_evidence e
LEFT JOIN forensic_verdicts v ON v.session_fingerprint = e.session_fingerprint
LEFT JOIN soar_actions s      ON s.session_fingerprint = e.session_fingerprint
LEFT JOIN ip_block ib         ON ib.ip_address = e.client_ip
GROUP BY e.session_fingerprint, e.client_ip, v.classification, v.confidence, v.verdict_json,
         s.rule_name, s.enforcement_status, ib.rule_name, ib.enforcement_status
ORDER BY MAX(e.timestamp) DESC
"""
