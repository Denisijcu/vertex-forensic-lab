# Prefacio

Este libro empezó con una pregunta incómoda: ¿qué pasa cuando el que ataca tu API ya no es un script,
sino un modelo?

Llevo meses construyendo agentes de IA. Agentes que leen documentos, que consultan bases de datos, que
usan herramientas a través del protocolo MCP, que deciden qué hacer a partir de lo que encuentran. Y
cuanto mejor funcionaban, más clara tenía una idea: todo lo que un agente hace para ayudar, otro agente lo
puede hacer para atacar. Leer la respuesta de un servidor, entender una pista en un mensaje de error,
pasarle a otro agente lo que encontró. La misma capacidad, con otra intención.

Las defensas que conocía estaban pensadas para otro enemigo. Un cortafuegos de aplicaciones reconoce
firmas: busca en cada petición algo que se parezca a un ataque conocido. Funciona contra un escáner que
repite siempre las mismas cargas. Contra un agente que escribe cada carga nueva y reparte el trabajo con
otro, mira en el sitio equivocado.

Así que construí un laboratorio para mirar en otro sitio. No en lo que dice cada petición, sino en cómo
llegan: cuánto desorden llevan, cuánto tiempo pasa entre ellas, y, sobre todo, si un cliente usa algo que
le dieron a otro. Le puse una trampa con firma criptográfica, un pozo de brea que hace pagar cada pregunta,
un perito que decide con evidencia y un botón que saca al atacante con una regla real de firewall. Y luego
lo ataqué desde mi propia máquina, con un Parrot en WSL, hasta que funcionó de verdad.

Por el camino aprendí más de lo que esperaba, y casi todo de los errores. Una media aritmética convirtió a
un escáner en un agente. Un indicador que parecía razonable acusaba a cualquiera. La API que disparaba los
bloqueos estaba abierta a la red, y el atacante podía usarla contra mí. Y el modelo local que redactaba los
dictámenes firmó, en siete de nueve sesiones, afirmaciones que la evidencia contradecía. Ese último error
me dejó la idea que más pesa de todo el libro: un modelo puede asistir, pero no puede dar fe.

Todos esos errores están aquí, con sus causas y sus correcciones. No por honestidad de cara a la galería,
sino porque son la parte más útil. El camino feliz lo encuentras en cualquier documentación. El que se
tuerce, y por qué se tuerce, solo lo encuentras en quien lo recorrió.

Como mis libros anteriores, este está hecho con hardware modesto, en las horas libres que dejan los turnos
de noche, y midiendo cada paso. Cada cifra que vas a leer salió de la bitácora del proyecto o del acta que
firmó el propio laboratorio. Ninguna es estimada.

Espero que te sirva para defender lo tuyo.

— Denis Sánchez Leyva
Miami, noviembre de 2026
