# Laboratorio: registro de pruebas

Cada vuelta del laboratorio (tarea programada) apunta aquí lo que probó, con qué datos y qué salió, también lo que no funcionó.
Regla: se ajusta solo con entreno (2018–21) y validación (2022–23); 2026 y el simulado en vivo son el juez.


## 2026-10-24 21:00 (hora de Madrid) — Candado semanal del equipo
- **Hipótesis:** los equipos fallan sobre todo por ganar solo el 45–48 % de las semanas. Si el equipo, cuando ya gana un X % en la semana, pasa a liquidez hasta el lunes, asegura esa semana en verde y debería subir el % de semanas ganadas sin romper la caída máxima.
- **Qué cambié (solo en pruebas, no en el código):** variante de `equipos.simulate` con candado X = 0,5 / 0,75 / 1 / 1,25 / 1,5 / 2 / 3 %. Cerrar cuesta el coste de reparto habitual (0,2 % del dinero movido). Comisiones USDC (sin cambio USDC/EUR: en el laboratorio no hay acceso a Bitvavo, se usan precios en euros).
- **Datos:** solo validación 2022 y 2023, con los 158 agentes examinados (sin clones). Equipos formados con un año (mismo método que `build`: 24 mejores y distintos, 27 combinaciones de prudencia y reparto) y probados en el otro, en los dos sentidos; y además 60 equipos al azar de 4 agentes, para no depender de la selección.
- **Resultado (mismos equipos, con y sin candado, año de prueba):**
  - Semanas ganadas: suben siempre. 2023: 49,8 % → 55,3 % (candado 1 %) / 58,7 % (0,5 %); al azar 41,6 % → 44,5–47,7 %. 2022: 32,2 % → 49,8–54,6 %; al azar 30,6 % → 39–43 %.
  - Rentabilidad: baja mucho en el año alcista. 2023 mediana +46 % → +10 % (candado 1 %), +1 % (0,5 %); al azar +25 % → +4 %. En 2022 (bajista) pierde menos: −45 % → −22 %.
  - Equipos que cumplen las 3 condiciones: casi igual. 2022→2023 con selección: 9 sin candado → 0 / 9 / 10 / 6 / 9 / 9 según X; al azar 10 → 10–12. En 2022 ninguno cumple con o sin candado (1 de 60 al azar con candado).
  - Formando los equipos ya con el candado, 2022→2023: 9 → 14 cumplen con X = 1 %, pero 11–12 con los demás X y 0 en 2023→2022: no es estable.
- **Conclusión: no se queda.** Cambia semanas en verde por rentabilidad: acerca una condición (más del 50 % de semanas) y aleja otra (+10 % al año). La mejora en equipos que cumplen todo depende del umbral y del año, no es robusta.
- **Nota para próximas vueltas:** en 2022 (bajista) ningún equipo cumple con nada de lo probado; el problema de fondo es ganar en mercados bajistas (cortos/tendencia diaria) y la falta de semanas con operaciones. Un candado solo tendría sentido combinado con algo que suba la rentabilidad.

## 2026-10-25 10:49 (hora de Madrid) — Filtro de tendencia diaria del equipo
- **Hipótesis:** en años bajistas los equipos se hunden porque siguen dando dinero a compras que van contra la tendencia. Si el equipo no pone dinero en una compra cuando el activo cierra por debajo de su media de N días (ni en un corto cuando cierra por encima), y reparte ese dinero entre los demás, deberían bajar las caídas y subir los equipos que cumplen. El agente sigue con su operación; solo el equipo se queda fuera (se puede hacer por la API: es simplemente no comprar esa parte).
- **Qué probé (en una copia):** variantes con media de 50 / 100 / 200 días, tendencia del propio activo o de BTC, y bloquear solo posiciones abiertas ("pos") o también la espera de agentes que solo compran ("todo"). Coste de reparto habitual (0,2 %). Comisiones USDC con cambio USDC/EUR.
- **Datos:** 168 agentes examinados (sin clones). Solo 2019–2021 (entreno) y 2022–2023 (validación); los datos se cortaron el 01/01/2024. Equipos formados con un año (mismo método que `build`) y probados en el siguiente (2019→20, 2020→21, 2021→22, 2022→23, 2023→22, 2021→23), y 60 equipos al azar de 4 agentes por año.
- **Resultado:**
  - "todo" es malo: deja semanas sin operar (cuentan como perdidas) → las semanas en verde caen (p. ej. 2022: 44 % → 10–18 %). Descartado.
  - Media de 200 días: menos caída pero menos equipos que cumplen en 2023 (5 → 2). Media de 100: mejora, pero menos que la de 50. BTC como referencia ≈ igual que el propio activo.
  - **Media de 50 días del propio activo, solo posiciones ("pos")**, formando los equipos ya con el filtro (como haría el código), equipos que cumplen las 3 condiciones en el año de prueba: 2019→20: 21/21 → 24/24; 2020→21: 11/24 → 19/27; 2021→22: 0 → 0 (pero mediana −40 % → +2 %, caída 40 % → 17 %); 2022→23: 5/24 → 15/27; 2023→22: 0 → 0 (−36 % → −12 %); 2021→23: 7/24 → 15/24. Al azar: 2019 29→43/60, 2020 49→59, 2021 45→57, 2022 0→0 (caída 39 % → 33 %), 2023 11→32. La caída máxima mediana baja en casi todos los casos; la rentabilidad baja algo solo en 2020 (año muy alcista).
  - Comprobado con el código ya integrado (no solo con el prototipo): mismos números de arriba.
- **Conclusión: se queda.** Mejora en todos los pares de años salvo los dos de 2022, donde sigue sin cumplir nadie pero pierde mucho menos. Integrado en `src/equipos.py` (`TENDENCIA_DIAS = 50`; la operación bloqueada lleva P = −1 y no recibe dinero) y el panel lo explica ("operación abierta contra la tendencia de 50 días: el equipo espera fuera").
- **Solo para informar (juez 2026, no se usó para decidir):** rehaciendo los equipos con el filtro, el podio en 2026 gana el 53 %, 53 % y 51 % de las semanas (antes 49–51 %), pero gana menos: 7,9 %, 5,2 % y 3,2 % al año (el Halcón sin filtro llegaba a ~12 % al año con el 51 % de semanas). Caídas 18–25 %. Es decir, en 2026 sube la condición de semanas y baja la de rentabilidad. Vigilar en simulado.
- **Para próximas vueltas:** en 2022 sigue sin cumplir ningún equipo; harían falta agentes que ganen en bajada (cortos con tendencia diaria) para que el dinero bloqueado trabaje en vez de esperar.

## 2026-10-25 15:15 (hora de Madrid) — Filtro de valor esperado en el reparto del equipo
- **Hipótesis:** el reparto prioriza por probabilidad^prudencia × ganancia, pero no mira cuánto se pierde si sale mal. Si el equipo no da dinero a las operaciones cuyo valor esperado (P × objetivo − (1 − P) × stop) es negativo o muy pequeño, y lo reparte entre las demás, deberían subir la rentabilidad y los equipos que cumplen.
- **Qué probé (en una copia, sin tocar el código):** la operación con valor esperado por debajo de un umbral queda bloqueada como las que van contra la tendencia (no recibe dinero). Umbrales 0, +1 % y +2 %. Todo lo demás igual (filtro de tendencia de 50 días incluido), comisiones USDC con cambio USDC/EUR.
- **Datos:** 168 agentes examinados (sin clones), historial de operaciones desde 2018, datos cortados el 01/01/2024. Equipos formados con un año (mismo método que `build`) y probados en otro (2019→20, 2020→21, 2021→22, 2022→23, 2023→22, 2021→23), y 60 equipos al azar de 4 agentes (prudencia 1 y 3) por año.
- **Resultado (equipos que cumplen las 3 condiciones en el año de prueba; base → EV>0 → EV>1 % → EV>2 %):**
  - Formados con selección: 2019→20 24/24 → 24/24 → 27/27 → 27/27; 2020→21 19/27 → 21 → 21 → 21; 2021→22 0 → 0 → 0 → 6/24; **2022→23 21/27 → 19 → 0 → 0** (rentabilidad mediana +41 % → +4 %); 2023→22 0 → 0 → 0 → 0; 2021→23 15/24 → 16 → 16 → 17.
  - Al azar (de 120): 2019 103 → 98 → 85 → 81; 2020 118 → 118 → 118 → 116; 2021 112 → 112 → 110 → 112; 2022 0 → 0 → 0 → 0; 2023 66 → 77 → 77 → 80.
  - Bloquea un 7 % (EV>0), 21 % (+1 %) y 25 % (+2 %) de las operaciones abiertas.
- **Conclusión: no se queda.** Con umbral 0 casi no cambia nada (unos años algo mejor, otros algo peor); con umbrales más altos hunde 2022→23 y 2019. No hay mejora clara ni estable. La estimación de pérdida (stop) de cada operación es poco fiable para filtrar.
- **Para próximas vueltas:** 2022 sigue siendo el año sin ningún equipo que cumpla; lo que falta son agentes que ganen en bajada, no un mejor reparto entre los que ya hay.

## 2026-10-25 21:35 (hora de Madrid) — Formar los equipos "con colchón"
- **Arreglo técnico (antes de probar):** en `equipos.build`, al quitar a los agentes que no ganan en 2024–25 no se quitaba también su columna de pérdida (`L`), así que el reparto de medio Kelly usaba el stop de otro agente. Corregido (`L = L[keep]`); entra ya en la formación de equipos de esta noche (lunes).
- **Hipótesis:** los equipos se eligen para cumplir justo las condiciones (más del 50 % de semanas, +10 % al año, caída ≤ 25 %) y fuera de esos años suelen quedarse cortos (2026: 49–51 % de semanas, ~10 % al año). Si al formarlos se les pide un colchón (p. ej. 55 % de semanas, +20 % al año, caída ≤ 20 %), deberían cumplir más veces en el año siguiente.
- **Qué probé (en una copia, sin tocar el código):** misma fórmula de `objective` con metas más exigentes: suave (52,5 % / +15 % / 22,5 %), colchón (55 % / +20 % / 20 %), fuerte (60 % / +30 % / 18 %); y otra distinta, "maxmin" (maximizar el margen más justo de las tres condiciones). Mismo método que `build` (24 mejores y distintos, 3 prudencias × 18 formas de repartir = 54 equipos), comisiones USDC con cambio USDC/EUR, filtro de tendencia de 50 días.
- **Datos:** 168 agentes examinados (sin clones), datos cortados el 01/01/2024. Equipos formados con un año y probados en otro: 2019→20, 2020→21, 2021→22, 2022→23, 2023→22, 2021→23.
- **Resultado (equipos de 54 que cumplen las 3 condiciones en el año de prueba; base / suave / colchón / fuerte / maxmin):**
  - 2019→20: 54 / 54 / 54 / 54 / 54 · 2020→21: 49 / 49 / 50 / 51 / 50 · 2021→22: 6 / 6 / 6 / 6 / 0
  - **2022→23: 37 / 38 / 44 / 26 / 33** · 2023→22: 0 / 0 / 0 / 0 / 0 · 2021→23: 23 / 23 / 23 / 26 / 1
  - Rentabilidad mediana parecida en todos salvo "fuerte" y "maxmin", que ganan mucho menos (2022→23: +27 % base, +11 % fuerte, +11 % maxmin).
- **Conclusión: no se queda.** La mejora del "colchón" sale casi toda de un solo par de años (2022→23) y no va en una dirección: con un colchón algo mayor ("fuerte") ese mismo par empeora (37 → 26). "maxmin" es claramente peor. No es robusto.
- **Para próximas vueltas:** 2022 sigue sin ningún equipo que cumpla con nada probado. Esta noche entran por primera vez en los equipos los gemelos en corto y el reparto de medio Kelly: medirlos en entreno/validación antes de tocar más la formación.
