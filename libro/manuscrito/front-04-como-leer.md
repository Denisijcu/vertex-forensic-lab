# Cómo leer este libro

El libro sigue el recorrido de una petición hostil por el laboratorio, de fuera hacia dentro, y después
el de la respuesta: contener, documentar y abrir la evidencia a otros. Se puede leer de corrido, y cada
capítulo deja algo funcionando.

- **Capítulos 1 y 2:** qué es un enjambre, qué hace el laboratorio y cómo está organizado.
- **Capítulos 3 a 5:** las medidas y las dos defensas activas: la trampa con firma y el tarpit.
- **Capítulo 6:** el perito, y por qué el modelo no firma nada.
- **Capítulos 7 y 8:** la contención, y cómo impedir que el atacante use tus propias defensas.
- **Capítulo 9:** el campo de tiro con Parrot y las cuatro rondas de pruebas.
- **Capítulos 10 y 11:** el acta firmada y el servidor MCP.
- **Capítulo 12:** lo que todavía falla.

Si tienes prisa por ver el laboratorio funcionando, lee el capítulo 1 y salta al 9: con el Apéndice A al
lado, puedes montar el campo de tiro y volver después a los capítulos que expliquen lo que veas.

## Lo que necesitas instalado

- **Windows 11** con PowerShell. Para que los bloqueos lleguen al firewall, una consola **como
  Administrador**.
- **Python 3.10 o superior**, con `fastapi`, `uvicorn`, `duckdb`, `pydantic` y `httpx`; y `mcp` para el
  servidor MCP.
- **Node.js 20** y **Angular CLI 19** para el panel.
- **WSL2** en modo de red NAT, con una distribución que tenga `bash` y `curl`. En el libro, Parrot.
- **LM Studio** con el modelo local del perito, si quieres sus comentarios. Es opcional.

## Convenciones

Cada comando del libro indica **desde qué carpeta** se ejecuta y **en qué consola**: PowerShell normal,
PowerShell como Administrador o la terminal de Parrot. En un laboratorio que toca el firewall del sistema,
ejecutar el comando correcto en la consola equivocada es la causa más común de que algo "no funcione".

Las rutas del libro son las de la máquina en la que se construyó el proyecto: el laboratorio vive en
`E:\vertex-forensic-lab`. Si lo pones en otro sitio, cambia la ruta base en `Start-VertexLab.ps1`.

Las cifras que aparecen en el texto salen de la bitácora del proyecto, `logs/bitacora.md`, y del acta
final que firmó el laboratorio. Cuando un número no se pudo medir, el libro lo dice.

## El repositorio

```
vertex-forensic-lab/
├── backend/                  gateway FastAPI, señuelos, SOAR y configuración
├── frontend/                 panel en Angular 19
├── vertex-forensic-mcp/      servidor MCP y su cliente de prueba
├── simulator/                emulador de enjambre para Docker
├── tmp/swarm_assault.sh      el ataque desde Parrot
├── forensic_coroner_llm.py   el perito
├── forensic_report_compiler.py  el acta con hash encadenado
├── Start-VertexLab.ps1       arranque
├── Stop-VertexLab.ps1        parada y limpieza de reglas
├── Invoke-VertexRelease.ps1  empaquetado con SHA-256
├── reports/                  actas exportadas
└── logs/bitacora.md          la bitácora del proyecto
```
