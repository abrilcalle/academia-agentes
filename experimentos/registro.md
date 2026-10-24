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
