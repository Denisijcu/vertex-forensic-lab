# Para quién es este libro

**Para desarrolladores backend** que exponen una API y quieren entender qué cambia cuando del otro lado
hay agentes de IA. No hace falta experiencia en seguridad: el libro explica cada concepto, del Canary
Token al tarpit, cuando lo necesita.

**Para equipos pequeños de seguridad**, o para la persona que hace de equipo de seguridad en una empresa
pequeña, que no pueden pagar una plataforma comercial y necesitan defensas que se entiendan, se midan y
se puedan defender ante un jefe, un cliente o un auditor.

**Para quien construye agentes**, porque conocer cómo se detecta a un agente hostil es la mejor forma de
entender qué puede hacer el tuyo, y qué puede hacer alguien con él.

**Para quien trabaja con modelos de lenguaje en sistemas con consecuencias.** El capítulo 6, sobre por
qué el modelo no puede firmar el dictamen, vale para cualquier sistema en el que un texto generado acabe
en un documento que otro va a usar para decidir.

## Lo que necesitas saber

- **Python** a nivel intermedio: funciones, módulos, un poco de programación asíncrona.
- **Algo de HTTP**: qué es una cabecera, un código de estado, un parámetro de consulta.
- **Un poco de SQL**: el libro usa consultas de agregación sencillas sobre DuckDB.
- **Manejarte en PowerShell y en bash**, lo justo para lanzar comandos y leer su salida.

No necesitas saber Angular. El panel se usa, pero no se programa en el libro.

## Lo que no es este libro

No es un manual de ataque. El atacante de estas páginas es un script propio, lanzado desde una máquina
propia contra un honeypot propio, con el único fin de comprobar que las defensas funcionan.

Tampoco es un producto listo para producción. Es un laboratorio: un sitio donde entender, medir y
equivocarse sin consecuencias. El capítulo 12 dice con detalle qué le falta para salir de él.
