# Guion de demo — 3 minutos

El objetivo no es "miren lo que construimos", sino **"miren lo que nadie comprueba y nosotros
sí, sin acusar en falso y sin soltar un número de más"**.

## Antes de entrar (5 minutos antes)

```bash
# 1. La clave, si no está
test -f .env || echo 'NAN_KEY=tu-clave' > .env

# 2. Backend con el modelo real (comprobar que dice provider nan)
cd server && uv run uvicorn ficha_tecnica.api.app:app --port 8000
curl -s http://127.0.0.1:8000/v1/health        # -> {"status":"ok","provider":"nan"}

# 3. Web, en otra terminal
pnpm --dir web dev
```

Checklist:

- [ ] `provider` dice **nan**. Si dice `mock`, la ficha es de mentira y el jurado puede notarlo.
- [ ] La pestaña está en <http://127.0.0.1:5173> con el campo vacío.
- [ ] El texto de la demo está en el portapapeles, no escrito a mano en vivo.
- [ ] Los tres textos de abajo están en un archivo abierto, listos para pegar.
- [ ] Plan B: `informe.md` abierto en la tabla de medición, por si la red falla.

Ensayalo una vez completo. La ficha tarda entre 0,4 y 1,8 segundos: la demo se sostiene sola,
no hace falta relleno.

## 0:00 — El problema

> "Hay encuestas en todas las noticias y casi nadie comprueba si la noticia da lo necesario
> para interpretarlas. Este titular dice quién gana. ¿Podés saber con eso si la encuesta
> aguanta? Ni vos ni yo. Y la noticia no te lo va a decir."

## 0:25 — Pegar y analizar (noticia incompleta)

Pegá el **texto B** (abajo) y pulsá Analizar.

> "Semáforo rojo. No dice cuántas personas fueron entrevistadas, no dice el margen, no dice
> quién la encargó. La aplicación no opina del resultado: te dice qué falta."

**Señalá el aviso legal de la cabecera**: *"No es asesoramiento jurídico: la valoración
corresponde a la Junta Electoral Central."*

## 1:00 — Abrir un ítem y ver la evidencia

Clic en la fila **"Margen de error"**.

> "Acá está la frase exacta del texto que lo demuestra, resaltada sobre tu propia noticia.
> La app no inventa la cita: te muestra dónde mirar, y abajo la probabilidad del modelo con
> la versión del cuestionario."

**Punto clave para el jurado:** la app devuelve **posiciones**, no frases. El texto no se
regenera y no se guarda: en la base solo queda un hash.

## 1:25 — La noticia completa (verde)

Pegá el **texto A**.

> "Misma encuesta, ahora con la ficha técnica completa: verde. Y fijate en lo que **no** ves:
> ningún número de intención de voto, ningún nombre de partido en ningún hallazgo. No es un
> olvido: es una regla dura, y hay un detector independiente que verifica que no se filtre."

## 1:50 — La prueba de fuego: una paráfrasis

Pegá el **texto C** (mismo contenido que A, otra redacción).

> "Esto es exactamente lo mismo, escrito distinto: 'error muestral' en vez de 'margen de
> error', 'encuestados' en vez de 'entrevistas'. Sigue verde. Si el sistema acusara acá,
> estaría acusando en falso a un medio por cómo escribió, no por lo que dijo."

## 2:15 — Los números

Mostrá `informe.md`, sección de medición.

> "Sobre el corpus sintético, con el modelo real: **cero por ciento de falsa acusación** en
> 165 ítems, **86,67 % de recall** de omisiones reales, diez por ciento en 'revisar a mano',
> cero fugas del saneador, y entre 0,4 y 1,8 segundos por ficha.
>
> Y una limitación que preferimos decir: los otros dos sistemas de la comparación son jueces
> LLM y no pudimos medirlos, así que no los graficamos. Preferimos un hueco declarado a un
> número inventado."

## 2:40 — La veda

Reiniciá el backend con la fecha simulada:

```bash
VEDA_NOW=2026-11-25T10:00:00+01:00 uv run uvicorn ficha_tecnica.api.app:app --port 8000
```

Pegá el texto A otra vez.

> "Durante los cinco días previos a la votación, la ley prohíbe publicar sondeos electorales.
> Analizar no es publicar, pero preferimos no arriesgar: la app se niega y explica por qué.
> Las encuestas de otros temas se siguen analizando."

Cierre:

> "No dice si la encuesta es verdadera. Dice si la noticia te da lo necesario para juzgarla.
> Y cuando no está seguro, lo dice."

## Los tres textos

**A — ficha completa (verde)**

```
SIMULACIÓN. Demoscopia Ficticia S.L., con sede en la calle Imaginaria 12 de Madrid, realizó para la Fundación Imaginaria un sondeo telefónico con 1.200 entrevistas entre el 3 y el 8 de noviembre a personas con derecho a voto residentes en la comunidad. El margen de error es de 2,8 puntos para un nivel de confianza del 95 %. El muestreo fue aleatorio estratificado y las personas se seleccionaron por marcación aleatoria. Ante la pregunta «¿A qué formación votaría si se celebraran elecciones este domingo?», el 5 % no contestó. Los datos se ponderaron por sexo, edad y tamaño del municipio.
```

**B — sin muestra ni margen (rojo)**

```
SIMULACIÓN. Según un sondeo de Demoscopia Ficticia S.L., el Partido Popular ganaría las elecciones. El Partido Popular obtendría un 34 % de los votos y el PSOE un 26 %.
```

**C — la misma que A, parafraseada (verde)**

```
SIMULACIÓN. El estudio de Demoscopia Ficticia S.L., cuya sede está en la calle Imaginaria 12 de Madrid, fue encargado por la Fundación Imaginaria y se hizo por teléfono con 1.200 encuestados del 3 al 8 de noviembre, entre personas con derecho a voto de la comunidad. Presenta un error muestral de 2,8 puntos con una confianza del 95 %. El procedimiento fue un muestreo aleatorio estratificado con selección por marcación aleatoria. A la pregunta «¿A qué formación votaría si se celebraran elecciones este domingo?» no respondió el 5 %. Los resultados se ponderaron por sexo, edad y tamaño del municipio.
```

Los tres están verificados contra el modelo real y el código de `dev`. Si algún texto cambia
de color, **no es la demo**: es un bug, y conviene saberlo antes de entrar.

## Si algo falla en vivo

| Fallo | Qué hacer |
|---|---|
| El backend no responde | Reiniciarlo; si no arranca, mostrar la numeración de la tabla de medición y seguir hablando |
| `provider` dice `mock` | Decirlo en voz alta: "esto es el modo sin modelo, para ver el flujo". No fingir |
| La ficha tarda | "está hablando con el modelo en vivo", que es la verdad |
| Sale un ítem en gris que esperabas verde | Es una oportunidad, no un problema: "acá la app prefirió no decidir" |
| La veda no bloquea | Comprobar `VEDA_NOW` en el entorno del proceso |

## Lo que no se muestra

- No se muestra el panel interno de evaluación: no hace falta y no está en la interfaz.
- No se pega una noticia real que esté dentro de la ventana de veda.
- No se promete comparación contra jueces LLM: no está medida.
