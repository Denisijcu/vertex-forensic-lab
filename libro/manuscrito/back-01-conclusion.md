# Conclusión — Cuando el atacante también es un modelo

Empecé este libro con una idea sencilla: si el atacante ahora razona, la defensa tiene que dejar de
buscar firmas y empezar a observar comportamientos. Doce capítulos después, creo que la idea sigue en pie,
pero el camino me enseñó tres cosas que no esperaba.

**La primera es que la mejor prueba contra un enjambre no es estadística, sino criptográfica.** La
entropía, la cadencia y el User-Agent son indicios útiles, y el libro les dedica un capítulo entero. Pero
todos se pueden discutir, ajustar o falsificar. Un agente puede escribir cargas más ordenadas, variar sus
tiempos o mentir sobre quién es. Lo que no puede hacer es presentar un token firmado con la identidad de
otro cliente sin delatar que ese otro cliente se lo pasó. Las 12 transferencias del acta final no
dependen de ningún umbral. Son la prueba más sólida que produjo el laboratorio, y la única que seguiría
funcionando contra un atacante que no declarase su framework.

**La segunda es que las defensas son objetivos.** El fallo más grave del proyecto no estaba en la
detección, sino en la herramienta de contención: una API capaz de crear reglas de firewall, abierta a la
red. Cuanto más poder le das a un sistema de defensa, más atractivo es para el atacante, y más tiene que
protegerse a sí mismo. La pregunta que hay que hacerle a cada función con poder no es "¿funciona?", sino
"¿qué pasa si la llama otro?". Y esa pregunta solo se responde mirando el sistema desde el otro lado de la
red.

**La tercera es la que le da título al capítulo 6, y es la que me llevo a todo lo demás que construya.**
Un modelo de lenguaje puede asistir muy bien: puede leer evidencia, resumirla, sugerir una lectura,
redactar un borrador. Pero dar fe es otra cosa. Dar fe es firmar que algo es verdad, y eso exige que cada
afirmación se pueda rastrear hasta un dato. El modelo del perito recibió la clasificación hecha y los
indicadores confirmados, y aun así escribió, en siete de nueve sesiones, cifras que contradecían la
evidencia que tenía delante. No por malicia, sino porque un texto generado suena igual de seguro cuando
acierta que cuando se equivoca. En un acta forense, como en cualquier documento que otro va a usar para
decidir, el modelo puede ser el asistente del perito. No puede ser el perito.

Hay una cuarta lección, más modesta, que atraviesa el libro entero: **solo sabes lo que has medido.** La
media que convirtió a un escáner en un agente, el puntaje del tarpit que nunca olvidaba, el suelo de 0.2
segundos que ponía cada conexión a la base de datos, la API que respondía a cualquiera: nada de eso se veía
en el código. Se vio en la consola de Parrot, en el panel y en el acta. Un laboratorio no sirve para
demostrar que tu defensa funciona. Sirve para descubrir dónde no funciona, antes de que lo descubra otro.

Vertex Forensic Lab no es el final de nada. El capítulo 12 deja una lista de lo que le falta, y la prueba
que de verdad importa, ponerlo delante de agentes reales, todavía está por hacer. Pero el ciclo completo ya
existe y ya se probó con tráfico real: detectar al enjambre, hacerle pagar cada paso, peritarlo con
evidencia, dejarlo fuera con una regla real y firmar un acta de la que se puede responder línea a línea.

El enemigo cambió. Ahora sabes cómo mirarlo.
