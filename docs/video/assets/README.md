# Capturas para la demo

Capturadas el 14/11/2026 con el navegador de Orca sobre la aplicación en marcha
(`http://127.0.0.1:5173`, proveedor `nan`), con el código de `dev`.

| Fichero | Caso | Entrada | Resultado observado |
|---|---|---|---|
| `01-url-real-euronews.png` | Noticia real | Modo **Enlace**, URL de Euronews (13/11) | Semáforo **rojo**; entidad, muestra, margen y universo presentes; domicilio y quién encargó ausentes |
| `02-texto-completo-verde.png` | Ficha completa | Texto A, modo Texto | Semáforo **verde**, 13 presentes y 2 ausentes |
| `03-evidencia-resaltada.png` | Evidencia | Texto A con la fila «Margen de error» abierta | `<mark>` sobre «El margen de error es de 2,8 puntos…» en el texto del usuario, con `Probabilidad de Clef: 99 %` |
| `04-texto-incompleto-rojo.png` | Noticia incompleta | Texto B | Semáforo **rojo**, 14 ausentes |
| `05-parafrasis-verde.png` | Paráfrasis (M14) | Texto C | Semáforo **verde**, idéntico a `02` |

## Sobre 02 y 05

Son **byte a byte idénticas** (`sha256 a00b788662b2…`), y eso no es un fallo de captura: es el
resultado. El texto C dice lo mismo que el A con otras palabras —«error muestral» por «margen
de error», «encuestados» por «entrevistas»— y la ficha sale igual.

Para el vídeo eso es un recurso, no un problema: un fundido entre las dos imágenes demuestra
en dos segundos que el sistema no acusa por cómo está escrita la noticia. Si se quieren como
dos planos distintos, conviene desplazar una de ellas para que el corte se note.

## Lo que no está capturado

- **Pantalla de veda**: requiere reiniciar el backend con `VEDA_NOW` dentro de la ventana
  (24–29 de noviembre). Pendiente si se quiere incluir el cierre de la demo.
- **Estado gris** («no parece una encuesta»): con el texto de la receta.

## Cómo se generaron

1. Crear pestaña en `http://127.0.0.1:5173`.
2. Elegir **Texto** o **Enlace** y aportar la noticia.
3. Pulsar **Analizar** y esperar la ficha.
4. `orca screenshot --format png --json` y copiar el `path` resultante.

Las capturas muestran la ventana del navegador tal cual, a 1600 px de ancho. La interfaz no
imprime nombre de partido ni cifra de estimación en ningún hallazgo, por eso no aparecen.
