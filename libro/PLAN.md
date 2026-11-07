# Plan del libro — *Vertex Forensic Lab*

**Subtítulo (propuesta):** Cazar enjambres de agentes de IA con señuelos, tarpit, un perito local y contención real
**Autor:** Denis Sánchez Leyva — Vertex Coders LLC
**Idioma:** español · **Enfoque:** práctico, defensivo, solo la versión final (v1.3)
**Formato:** el mismo que *Vertex-Core SQL*: un `.md` por capítulo en `libro/manuscrito/` y el interior para KDP en 6x9 in (pandoc + XeLaTeX, con el `build_pdf.py` adaptado)

**Reglas del manuscrito**
- Todas las cifras salen de `logs/bitacora.md` y del acta `reports/ACTA_FORENSE_VERTEX_20261106_152518.md`. Nada estimado.
- Cada capítulo abre con la nota "> Borrador. Fuente: ..." (el build la quita) y cierra con "Lo que te llevas de aquí".
- Enfoque **defensivo**: el ataque desde Parrot se presenta como banco de pruebas propio, en una red local, contra un honeypot propio. No se enseñan técnicas de ataque contra terceros.
- No se habla de versiones anteriores como producto. Los errores (el falso positivo por la media de Δt, el `curl` que tocaba la trampa, los dictámenes falsos del LLM, el hueco de la superficie de mando) se cuentan como decisiones y trampas del propio proyecto.
- Los nombres de modelos de terceros no aparecen; el perito local es "el modelo local `vertex-core-sec-turn`".

---

## Preliminares
- **Portada y créditos.**
- **Dedicatoria** para la madre de Denis, como en todos sus libros. *El texto lo confirma Denis.*
- **Prefacio:** por qué un laboratorio contra enjambres de agentes y por qué en casa.
- **Para quién es:** desarrolladores backend, equipos pequeños de seguridad y cualquiera que exponga APIs a agentes de IA.
- **Cómo leer este libro:** qué hace falta (Windows 11, Python, Node, WSL con Parrot, LM Studio opcional) y cómo está organizado el repositorio.

## Cuerpo

| # | Capítulo | Contenido | Fuente |
|---|---|---|---|
| 1 | **El enemigo cambió** | Qué es un enjambre (un Scout que explora y un Exploit que ataca con lo que encontró) y por qué un WAF de firmas no ve la relación. El laboratorio terminado y los resultados por adelantado: la tabla del acta final | bitácora 15:25, acta final |
| 2 | **Cinco capas y una sola verdad** | Gateway FastAPI, bóveda DuckDB, perito, HUD Angular y MCP. `lab_env.py` como única fuente de configuración (`.env`, `DB_PATH`, umbrales) y por qué tres copias de una misma cifra acaban diciendo tres cosas distintas | código v1.3, bitácora 14:42 |
| 3 | **Medir la física del tráfico** | Huella sin estado (SHA-256 de IP, User-Agent y nodo), entropía de Shannon y Δt. **El caso del Nikto que parecía un agente:** la media de 46 381 ms frente a la mediana real de 223.5 ms, y por qué la cadencia se mide dentro de cada ráfaga | bitácora 15:06, acta |
| 4 | **Una trampa con firma** | El endpoint señuelo, el Canary Token HMAC-SHA256 y el linaje Scout → Exploit (`LATERAL_SWARM_HANDOFF`). El token alterado que tumbaba el middleware. Los 12 handoffs de Parrot, de 1.8 s a 17.5 s | bitácora 14:42, 15:25 |
| 5 | **Que cada pregunta le cueste** | El tarpit adaptativo: pesos, curva exponencial y tope de 6 s. Medido: Nikto 0.2 s, Exploit 6.4 s. El hallazgo del puntaje que nunca baja, y el costo de abrir DuckDB en cada petición | bitácora 15:00, 15:03 |
| 6 | **El modelo asiste, no da fe** | El perito híbrido: indicadores que deciden frente a contexto que no decide, y por qué "tocar la trampa" no prueba nada. El 400 de la carga del modelo. **7 de 9 dictámenes falsos**, el validador frase a frase y el dictamen oficial determinista | bitácora 15:06, 15:22 |
| 7 | **Contener sin dispararse en el pie** | El SOAR: validación con `ipaddress` sin pasar nada al shell, la salvaguarda de loopback, reglas sin duplicados, `LOGICAL_BLOCK_ONLY` y el bloqueo por IP que cubre todas las sesiones de un atacante | `soar.py`, bitácora 15:13–15:18 |
| 8 | **Que no te usen el escudo** | El hueco más grave del proyecto: una API de bloqueo abierta a la red. Superficie de mando solo en loopback (middleware y dependencia), 403 registrado como `ADMIN_SURFACE_PROBE`, CORS acotado, regla de entrada solo para la subred WSL y secretos en `.env` | bitácora 14:34, 15:03 |
| 9 | **Campo de tiro: Parrot contra Windows** | WSL2 en modo NAT y la subred `172.28.48.0/20`. El conflicto de red de Docker. `swarm_assault.sh` en cuatro fases. Las cuatro corridas, el script viejo, el desfase entre handoff y evidencia, y la prueba de fuego: Parrot fuera | bitácora 14:56–15:17 |
| 10 | **Un acta que se pueda defender** | La exportación firmada: hash del cuerpo frente a hash del archivo, la consulta única del HUD y del acta (`session_queries.py`) y el compilador con hash encadenado | `main.py`, `forensic_report_compiler.py`, bitácora 15:18–15:25 |
| 11 | **Un agente que consulta la bóveda** | El servidor MCP: las cuatro herramientas, el módulo SOAR compartido y la prueba de inyección `1.2.3.4; whoami` en `client_test.py` | `vertex-forensic-mcp/` |
| 12 | **Lo que todavía falla** | Los pendientes medidos: el puntaje del tarpit sin decaimiento, una conexión DuckDB por petición, la etiqueta del Scout, indicadores solapados y el despliegue Docker sin probar. Plan de la v1.4 | bitácora "Pendientes" |

## Final
- **Conclusión:** lo que cambia cuando el atacante también es un modelo.
- **Apéndice A — Comandos de operación**, en orden, con el directorio y la consola (normal o Administrador) de cada uno.
- **Apéndice B — Glosario:** enjambre, honeypot, Canary Token, HMAC, tarpit, entropía de Shannon, SOAR, MCP, etc.
- **Apéndice C — Referencia técnica:** esquema de las cuatro tablas DuckDB, estados SOAR, etiquetas de engaño y variables de entorno.
- **Sobre el autor** (se adapta el de *Vertex-Core SQL*).

**Extensión estimada:** 12 capítulos de 2.500 a 3.500 palabras, unas 150–180 páginas en 6x9.

## Orden de trabajo
1. Aprobar este plan (título, subtítulo, capítulos).
2. Escribir capítulo por capítulo; cada uno se revisa antes de pasar al siguiente.
3. Preliminares y final.
4. Compilar el PDF 6x9 y el EPUB, la portada y la ficha de KDP.
