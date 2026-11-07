# Capítulo 10 — Un acta que se pueda defender

> Borrador. Fuente: backend/main.py (export_forensic_report), backend/session_queries.py,
> forensic_report_compiler.py, logs/bitacora.md (6 de noviembre de 2026, entradas de las 15:18, 15:22 y 15:25)
> y las dos actas de ese día.

Un incidente que no queda documentado no existió. Puede que lo hayas detectado, frenado y contenido
perfectamente, pero si mañana alguien pregunta qué pasó, quién fue, qué hiciste y por qué, la respuesta
tiene que estar en un documento. Y ese documento tiene que resistir dos preguntas incómodas: ¿es
correcto? y ¿alguien lo ha cambiado desde que se escribió?

La primera pregunta la responden los capítulos anteriores: cada cifra del acta sale de la bóveda, y
cada dictamen se construye con indicadores verificables. Este capítulo responde la segunda, y cuenta
también qué **no** puede responder un hash, para que no le pidas más de lo que da.

## Lo que contiene el acta

El botón **EXPORTAR ACTA SHA-256** del panel llama a `/api/actions/export-report`, que genera un
documento Markdown en la carpeta `reports/` con cuatro secciones:

1. **Resumen de sesiones auditadas.** Una fila por huella: IP, User-Agent, peticiones, cadencia
   mediana, entropía máxima, veredicto, certeza y regla de firewall con su estado.
2. **Trazabilidad de enjambres.** Una fila por cada uso de un Canary Token: el Scout, el Exploit, el
   tiempo de tránsito y la ruta atacada.
3. **Dictámenes periciales.** Por cada sesión, sus etiquetas de engaño, el dictamen oficial y el estado
   de contención.
4. **Sello criptográfico.** La huella SHA-256 del contenido.

La cabecera deja constancia de cuatro datos que cualquiera que lea el acta necesita para interpretarla:
la versión del laboratorio, la fecha de emisión en UTC, la ruta de la bóveda de la que salen los datos y
el umbral de entropía con el que se clasificó.

## Una sola consulta para el panel y para el acta

La sección 1 del acta y las tarjetas del panel muestran lo mismo: un resumen por sesión. Antes de la
revisión, cada uno tenía su propia consulta SQL. El capítulo 3 contó una consecuencia: el panel
mostraba el Δt medio mientras el perito razonaba con la mediana. Y el capítulo 7, otra: el panel
marcaba el bloqueo por huella mientras el firewall bloqueaba por IP.

Las dos consultas ahora son una, `SESSION_SUMMARY_SQL`, en `backend/session_queries.py`. El panel la usa
para dibujar las tarjetas y el acta para escribir su tabla:

```python
sessions = [
    tuple(r[:10]) + (r[10] or "NO_APLICADA", r[11] or "SIN_AISLAR")
    for r in conn.execute(SESSION_SUMMARY_SQL).fetchall()
]
```

La única diferencia es cosmética: donde el panel deja un hueco vacío, el acta escribe `NO_APLICADA` o
`SIN_AISLAR`, porque en un documento escrito un vacío se puede leer como un olvido.

Esto importa más de lo que parece. Si el operador toma una decisión mirando el panel y el acta dice
otra cosa sobre la misma sesión, cualquiera que revise el incidente tendrá razones para dudar de los
dos. Que salgan de la misma consulta no garantiza que sean correctos, pero garantiza que, si se
equivocan, se equivocan igual, y el error se corrige en un solo sitio.

## Dos hashes, a propósito

El acta lleva dos huellas SHA-256, y conviene entender por qué son distintas.

La primera se calcula sobre el **cuerpo** del acta, las secciones 1 a 3, y se escribe dentro del propio
documento, en la sección 4:

```python
content_body = "\n".join(lines)
body_hash = hashlib.sha256(content_body.encode("utf-8")).hexdigest().upper()

final_markdown = (
    f"{content_body}\n---\n\n"
    f"## 4. Sello Criptográfico de Cadena de Custodia\n"
    f"- **Algoritmo:** `SHA-256`\n"
    f"- **Firma de Integridad del Cuerpo Pericial:** `{body_hash}`\n"
)
```

Un documento no puede contener su propio hash, porque al escribirlo cambia. Por eso se sella el cuerpo,
y el sello se añade después.

La segunda huella se calcula sobre el **archivo completo**, ya con el sello dentro, y se guarda en un
archivo aparte con el mismo nombre y la extensión `.sha256`:

```python
file_hash = hashlib.sha256(report_path.read_bytes()).hexdigest().upper()
(reports_dir / f"{report_filename}.sha256").write_text(f"{file_hash}  {report_filename}\n", encoding="utf-8")
```

El formato de ese archivo, el hash seguido de dos espacios y el nombre, es el estándar de las
herramientas `sha256sum`, así que se puede verificar con ellas sin escribir nada.

En la primera acta del 6 de noviembre, el panel mostró el hash del archivo, que empezaba por
`DAFFEFA1ED8D26CE`, mientras que el sello interno del cuerpo empezaba por `00CF758BA7E9A3A5`. Parece
una contradicción, pero son dos medidas de dos cosas distintas, y las dos son necesarias. La del archivo
detecta cualquier cambio en cualquier byte. La del cuerpo permite verificar el contenido aunque alguien
lo copie a otro documento o cambie el formato del final de línea.

## Cómo se verifica

Verificar el archivo completo, en PowerShell, desde la carpeta `reports`:

```powershell
Get-FileHash .\ACTA_FORENSE_VERTEX_20261106_152518.md -Algorithm SHA256
Get-Content .\ACTA_FORENSE_VERTEX_20261106_152518.md.sha256
```

Si los dos hashes coinciden, el archivo no ha cambiado desde que se exportó.

Verificar el cuerpo exige separar el cuerpo del sello, exactamente como lo hizo el laboratorio. Un
pequeño script de Python, desde la misma carpeta, lo hace:

```python
import hashlib, sys
texto = open(sys.argv[1], encoding="utf-8").read()
cuerpo = texto.split("\n---\n\n## 4. Sello Criptográfico", 1)[0]
print(hashlib.sha256(cuerpo.encode("utf-8")).hexdigest().upper())
```

El resultado tiene que coincidir con la "Firma de Integridad del Cuerpo Pericial" de la sección 4. En el
acta final, esa firma es:

```
E1773E9F167D9AE81FB3A54E87B81F726439FFED61CB71E02908662E33A2ADCF
```

## Lo que un hash no prueba

Aquí tengo que ser preciso, porque es fácil sobrevalorar lo que hace un SHA-256.

Un hash prueba **integridad**: que el documento no ha cambiado desde que se calculó el hash. No prueba
**autoría** ni **momento**. Cualquiera que tenga la bóveda y el código puede generar un acta nueva, con
su propio hash, y ese hash será igual de válido. Un atacante que tuviera acceso a la carpeta `reports`
podría modificar el acta, recalcular los dos hashes y sustituir el archivo `.sha256`, y la verificación
seguiría saliendo bien.

Para que el acta pruebe también quién la emitió y cuándo, haría falta algo más: una **firma digital** con
una clave privada que solo tenga el laboratorio, o un **sello de tiempo** emitido por un tercero de
confianza, o, como mínimo, guardar el hash en un sitio que el atacante no controle: enviarlo por correo,
anotarlo en un registro externo o publicarlo. Nada de eso está en la versión actual, y lo cuento en el
capítulo 12.

Lo que sí da el hash, y no es poco, es una forma inmediata de detectar cualquier cambio posterior
accidental o malicioso en un acta que alguien ha archivado fuera del alcance del atacante. El paquete de
release del laboratorio hace lo mismo: el script `Invoke-VertexRelease.ps1` comprime el proyecto, calcula
su SHA-256 y lo guarda junto al zip.

## Más fuerte: el hash encadenado

El laboratorio tiene un segundo generador de informes, `forensic_report_compiler.py`, pensado para
cuando importa la integridad de toda la línea de tiempo y no solo del documento. Hace dos cosas que el
acta del panel no hace.

La primera es sellar **la propia bóveda**: calcula el SHA-256 del archivo `telemetry.duckdb` antes de
leerlo, para que el informe diga exactamente qué estado de la base de datos describe.

La segunda es un **hash encadenado** sobre todas las evidencias, en orden cronológico:

```python
chain_digest = hashlib.sha256(b"VERTEX_FORENSIC_GENESIS_SEED").hexdigest()
for r in rows:
    record_str = f"{chain_digest}|{r[0]}|{r[1]:.6f}|{r[2]}|{r[3]}|{r[4]}"
    chain_digest = hashlib.sha256(record_str.encode("utf-8")).hexdigest()
```

Cada eslabón incluye el hash del anterior. Si alguien borra, cambia o reordena una sola evidencia de la
mitad de la tabla, cambian todos los hashes que vienen detrás, y el hash final ya no coincide. Es la
misma idea de las cadenas de bloques, sin nada más: una forma de que la historia completa dependa de
cada uno de sus pasos.

Este generador tenía dos errores que corregí en la revisión. Consultaba dos columnas, `verdict_id` y
`analyzed_at`, que no existen en la tabla de veredictos, así que fallaba en cuanto había alguno. Y su
anexo de "reglas de contención" generaba comandos `netsh` para todas las IPs de la bóveda, incluida
`127.0.0.1`: alguien que copiara ese anexo y lo ejecutara se bloquearía a sí mismo. Ahora lee las
columnas reales, usa el dictamen oficial y sus indicadores, y deja fuera las IPs de loopback.

Desde la carpeta del laboratorio:

```powershell
python forensic_report_compiler.py
```

## El acta que se puede defender

Con todo lo anterior, el acta final del 6 de noviembre es un documento del que puedo responder línea a
línea. Cada fila de la sección 1 sale de la misma consulta que vio el operador en el panel. Cada una de
las 15 transferencias de la sección 2 es una fila de `swarm_lineage` con dos huellas distintas. Cada
dictamen de la sección 3 es una lista de indicadores que se pueden comprobar con una consulta SQL. Y el
sello de la sección 4 permite comprobar que nada de eso ha cambiado.

No es el documento más bonito que podría haber producido. Un modelo de lenguaje lo habría redactado con
más soltura, y en la primera versión lo hizo. Pero aquella acta, la de los dictámenes redactados por el
modelo, decía en siete de sus nueve sesiones cosas que la evidencia contradecía. Esta dice menos, y lo
que dice es verdad.

## Lo que te llevas de aquí

- Un acta tiene que resistir dos preguntas: si es correcta y si alguien la ha cambiado.
- El panel y el acta salen de la misma consulta. Si se equivocan, se equivocan igual, y se corrigen en
  un solo sitio.
- Hay dos hashes a propósito: el del cuerpo, escrito dentro del acta, y el del archivo completo, en un
  `.sha256` aparte con formato estándar.
- Un hash prueba integridad, no autoría ni momento. Para eso harían falta una firma digital, un sello de
  tiempo o guardar el hash fuera del alcance del atacante.
- El hash encadenado hace que la integridad de toda la línea de tiempo dependa de cada evidencia.
- Un anexo de comandos generado automáticamente puede ser peligroso: el compilador antiguo proponía
  bloquear `127.0.0.1`.
