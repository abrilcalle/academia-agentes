# Academia de Agentes

Agentes de trading que aprenden solos sobre BTC-EUR (Bitvavo) y se ejecutan gratis cada día en GitHub.

## Cómo aprende cada agente
1. **Nace** con un nombre, una temporalidad (velas de 1 día, 4 horas o 1 hora) y una personalidad: prudente, equilibrada o atrevida (cuánto le preocupan las caídas).
2. **Estudia (2018–2021):** prueba las estrategias conocidas (medias, rupturas de las Tortugas, RSI, Bollinger, MACD, momentum, control de volatilidad, stops ATR, RSI-2 de Connors y Kronos cuando haya previsiones) con sus parámetros, filtros y stops.
3. **Inventa (2018–2021):** parte de las 3 estrategias que mejor le fueron (y, si hay previsiones, de "ceñirse a Kronos") y crea reglas propias que va perfeccionando generación a generación (algoritmo evolutivo: se quedan las mejores, se cruzan y se cambian un poco). Sus reglas pueden combinar:
   - condiciones de entrada y salida (medias, máximos y mínimos, RSI, impulso, volatilidad, Bollinger, MACD, previsiones de Kronos);
   - **stop que sube con el precio** (a un 3, 5 o 10 % del máximo alcanzado, o a varias veces el ATR): si entra a 10 y sube a 14, el stop va subiendo y asegura casi todo el recorrido;
   - objetivo de beneficio fijo o **el precio que prevé Kronos**;
   - **cuánto arriesgar** en cada operación (20 %, 50 % o todo el fondo) o ajustarlo a la volatilidad;
   - tiempo máximo en una operación.
   - **figuras de chartismo**: doble suelo (W), doble techo (M), triple suelo, hombro-cabeza-hombro (normal e invertido), triángulo ascendente, bandera alcista / patrón N, rebote en soporte (zona de demanda), pérdida de soporte y ruptura con volumen alto;
   - **flujo de órdenes (order flow)**: delta (compras agresivas menos ventas agresivas, de Binance BTC/EUR desde 2020), absorción compradora y divergencia de delta. Solo el delta por vela: el libro de órdenes (layering) no tiene histórico gratuito;
   - **gestión activa de la operación** (sin apalancamiento): empezar con media posición y completarla si va a favor, subir el stop al precio de entrada al ganar un 2–5 %, acercar el stop si la operación no avanza en 1–7 días y ajustar el stop cada vez más cuanto más gana.
   Tras un stop o un objetivo, no vuelve a entrar hasta que aparezca una señal de entrada nueva.
4. **Elige (2022–2023):** compara su mejor estrategia conocida con la suya en dos años que no usó para ajustar nada y se queda con la que funciona mejor.
5. **Examen (2024–2025):** opera sin tocar nada. Aprueba si gana al menos un 10 % tras comisiones, hace 8 operaciones o más, no cae más de un 40 % y no opera igual que otro agente.
6. **Simulado:** los aprobados operan 90 días con 100 € ficticios y precios reales. Si caen más de un 25 % se retiran; si acaban con +5 % o más quedan **listos para dinero real** y siguen operando en simulado.

El primer día nacen 100 agentes; después, 10 nuevos cada día, para que siempre haya alumnos buscando un nuevo ganador.

## Operadores diarios

La mayoría de agentes nuevos (70 %) son **operadores diarios**: su objetivo es **acabar cada semana en positivo tras comisiones**, mejor si es +1 % o más (`objetivo_semanal_pct`). No tienen que operar cada día.

- Tienen **tres estrategias**, una para cada tipo de mercado (alcista, lateral y bajista), y un **detector de régimen** que decide cuál toca usar. En mercado bajista, como solo se compra al contado, pueden buscar rebotes cortos o quedarse en euros.
- Operaciones **cortas**: como mucho de 1 a 5 días, con velas de 1 o 4 horas. Pueden usar también condiciones de **hora del día y día de la semana** (estacionalidad).
- Se puntúan **semana a semana**: qué parte de las semanas acaba en positivo, cuántas llegan al +1 %, cuántas acaban en negativo, la ganancia media semanal y la peor semana.
- **Filtro anti-suerte**: tras inventar su estrategia se prueban 6 versiones con pequeños cambios en 2022–23; si la mayoría deja de ganar, se considera suerte y suspende.
- Exámenes: 2024–25 y 2026 con exigencias semanales (ver `operadores_diarios` en `config.json`).
- El panel muestra la **semana del equipo**: lo que ganan o pierden entre todos los agentes en simulado, semana a semana y ayer.

## Varios mercados, cortos y órdenes limitadas

- **Mercados:** BTC, ETH, SOL y oro (PAXG), en `config.json` → `activos`. Cada agente nace especializado en uno solo y estudia las ideas de internet de ese mercado (o las generales).
- **Ventas en corto sin apalancamiento** (operadores diarios): ganan cuando el precio baja, aplicando sus reglas al gráfico "dado la vuelta" y pagando el interés por hora del préstamo. Bitvavo las permite desde la app pero **todavía no por API** (dice que lo añadirá): los agentes que las usan salen marcados en el panel y no podrán pasar a dinero real hasta entonces. Se apagan con `permitir_cortos: false`.
- **Órdenes limitadas:** cada orden se pone al precio del último cierre (comisión 0,15 % en vez de 0,25 % y sin deslizamiento). Si el precio no la cruza en la vela siguiente, se ejecuta a mercado.
- **Herencia:** los agentes nuevos parten también de las reglas de los que ya van ganando en simulado (mismo mercado y temporalidad), y las mejoran.
- **Objetivo del equipo** (`objetivo_equipo`): al menos el 65 % de las semanas en verde, ninguna peor de −3 % y en positivo durante 3 meses. El informe mensual recomienda la combinación de agentes que más se acerca.

## Informe mensual
El día 1 de cada mes te llega un aviso y el panel muestra el informe del mes anterior:
- Cuánto ganó o perdió cada agente y cuántas operaciones perdió.
- **Qué combinación habría ganado más** con el mismo dinero (a toro pasado).
- **Quién amortiguó las pérdidas de quién:** "Elena perdió 3 operaciones (−11,90 €). En esos días Vera ganó +3,20 €: con Vera activada habrías perdido 3,20 € menos".
- **Agentes que se mueven igual**, porque tener varios así no reparte el riesgo.
- **Recomendación para el mes siguiente:** la combinación que mejor equilibra ganancia y caídas en los últimos 3 meses (no solo el último), sin juntar agentes que hacen lo mismo. Te dice a quién activar y a quién pausar.

**Tu cartera** son los agentes listos que no has pausado. Para pausar o reactivar, edita `config.json` → `cartera.pausados` (por ejemplo `["Marcos", "Sara"]`) o pídemelo.

Nada pasa a dinero real solo. Esa parte está sin hacer a propósito: se activará cuando tú lo decidas.

---

## Puesta en marcha
La forma fácil: conecta GitHub a Claude y pídele que lo instale. Si lo haces tú:

1. **Repositorio:** en github.com, **+ → New repository**, nombre `academia-agentes`, **Public**, **Create repository**. Sube todo el contenido de esta carpeta, incluida `.github`.
2. **Permisos:** Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.
3. **Avisos al móvil (opcional):** instala la app **ntfy**, suscríbete a un canal con un nombre difícil de adivinar (p. ej. `academia-7f3k9q2`) y guárdalo en Settings → Secrets and variables → Actions → New repository secret con el nombre `NTFY_TOPIC`.
4. **Panel:** Settings → Pages → Deploy from a branch → `main` / `/docs`. Quedará en `https://TU-USUARIO.github.io/academia-agentes/`. En el iPhone: Compartir → Añadir a pantalla de inicio.
5. **Primer día:** Actions → Academia diaria → Run workflow. El primero tarda más (crea 100 agentes y descarga años de velas por horas). Después se ejecuta solo cada noche.
6. **Kronos:** Actions → Rellenar histórico de Kronos → Run workflow, y repítelo hasta que el panel muestre las previsiones de Kronos al 100 %. Por defecto se calculan para velas diarias y de 4 horas (unas 22.000 previsiones desde 2018: varias tandas de 5 horas). Hasta llegar al 90 % los agentes estudian sin Kronos; los que nazcan después ya pueden usarlo.

## Ajustes (`config.json`)
| Ajuste | Qué hace |
|---|---|
| `comision_pct`, `deslizamiento_pct` | Coste de cada compra o venta (Bitvavo: 0,25 % en el nivel inicial) |
| `entreno`, `validacion`, `examen` | Años de cada fase |
| `aprobar_examen`, `simulado` | Mínimos para pasar de nivel |
| `fabrica.primera_promocion`, `agentes_nuevos_por_dia` | Cuántos agentes nacen |
| `fabrica.temporalidades` | Peso de cada temporalidad al crear agentes (`1d`, `4h`, `1h`) |
| `fabrica.poblacion_inventor`, `generaciones_inventor` | Cuánto se esfuerza cada agente al inventar |
| `cartera.pausados` | Agentes que no quieres en tu cartera |
| `informe_mensual` | Meses que mira la recomendación y tamaño de las combinaciones |

## Probar en tu ordenador
```
pip install numpy
python run_daily.py --sin-kronos
```

## Cosas a tener en cuenta
- **Muchos agentes, muchos aprobados por suerte.** Con 100 alumnos alguno aprobará por casualidad. Por eso el simulado en vivo es el filtro que cuenta, y el informe mensual sigue vigilando a los listos.
- **Inventar es fácil; inventar algo que funcione fuera del entreno, no.** Por eso la estrategia propia solo se elige si gana a la conocida en 2022–23, años que el agente no usó para ajustarla.
- **Velas de 1 hora = más operaciones = más comisiones.** Muchas estrategias rápidas mueren por eso. No se incluyen velas de 15 minutos: con las comisiones de Bitvavo casi nunca salen a cuenta.
- **Kronos pudo ver 2024–25 al entrenarse.** El modelo se publicó en 2025, así que los exámenes de agentes que usan Kronos pueden salir mejor de lo que son. Para ellos, solo el simulado en vivo es fiable.
- **Los stops se comprueban al cierre de cada vela** (cada hora, 4 horas o día según el agente), no en cada movimiento del precio.
- **La recomendación del informe no es una garantía.** Lo que mejor fue en los últimos meses puede no serlo el siguiente.
- Esto no es asesoramiento financiero. Resultados pasados no garantizan resultados futuros.
