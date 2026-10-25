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
