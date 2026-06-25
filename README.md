# Guía de exposición — Fase 1: A2C + DAgger (TurtleBot3)

*DS5345 · Aprendizaje por Refuerzo · Práctica de Laboratorio 4 (Sim to Real)*

Este documento tiene dos partes:
1. **Qué hice y por qué** (para explicarle a mi profesor).
2. **Comandos para la demostración en vivo** (para correr durante la expo).

---

# PARTE 1 — La lógica de lo que implementé

## El problema
Mi robot (TurtleBot3 Burger) debe navegar en Gazebo hacia una **meta fija** evitando **obstáculos móviles**, y aprender a hacerlo en el **menor tiempo posible**. Resolví esto en dos fases: primero un agente A2C que aprende por refuerzo, y luego DAgger para refinarlo imitando a un experto humano.

---

## Fase 1 — Agente base con A2C (sección 4.1)

### Por qué A2C y no DQN
DQN solo maneja **acciones discretas**. La consigna pide **acción continua**, así que usé **Actor-Critic**, que tiene dos componentes:
- el **Actor**, que propone directamente la acción continua, y
- el **Crítico**, que evalúa qué tan buena fue esa acción.

### Adaptación del entorno
Modifiqué el entorno para que la acción sea **continua y bidimensional**:
- velocidad lineal `v ∈ [0, 0.22]` m/s (límite cinemático real del burger),
- velocidad angular `ω ∈ [−ω_max, ω_max]` rad/s.

Lo definí como un **entorno Gymnasium con `gym.spaces.Box`**, y las acciones se envían a los motores con un mensaje `Twist` en el tópico `/cmd_vel`, como funciona ROS.

### El Actor Gaussiano
Mi Actor **predice la media (μ) y la desviación estándar (σ)** para `v` y `ω` a partir del estado. Con esa Gaussiana se muestrea la acción; la σ es la que da la **exploración**. El Crítico predice `V(s)`. Ambos comparten un tronco de capas y todo está en PyTorch.

### Función de recompensa (mi criterio de evaluación)
La diseñé para premiar exactamente lo que se evalúa:
- **+** por avanzar hacia la **meta fija**,
- **−** por cada paso (incentiva **rapidez**),
- **−** por **giros innecesarios** (proporcional a `|ω|`),
- **−** por estar cerca de obstáculos,
- **+200** por llegar, **−150** (drástico) por chocar.

### El algoritmo
Uso **GAE** para estimar la ventaja y actualizo con las **3 pérdidas de A2C**:
`L_total = L_actor + c_v·L_crítico − c_e·H(π)` (actuar + estimar valor + explorar), con normalización de ventajas y gradient clipping para estabilidad.

Al entrenar, guardo los pesos en **`a2c_sim.pth`** (como pide la consigna).

---

## Fase 2 — DAgger con experto humano (sección 4.2)

### La idea
DAgger no es refuerzo, es **imitación**: el robot copia a un **experto**. Según la consigna, el experto es un **humano que interviene con el teclado** (teleoperación).

### El pipeline que implementé
1. El agente **A2C entrenado pilotea** el robot (modo AUTO).
2. Cuando va a fallar, **yo intervengo con el teclado** (modo HUMANO) y lo guío.
3. Mientras intervengo, se **capturan los pares** `(estado, acción experta continua)`.
4. Con esos pares hago **fine-tuning por imitación**: minimizo el error (MSE) entre la acción que predice la red y la que yo ejecuté. Esto se hace **in situ**, sin parar la simulación.
5. **Valido**: vuelvo a AUTO y el robot se porta mejor en la zona donde lo corregí → aprendió de mi intervención.

Guardo el modelo refinado en **`a2c_dagger.pth`**.

### Resultado que obtuve
Capturé pares de intervención y al hacer el fine-tuning la **loss de imitación bajó hasta ~0.0009**, lo que confirma que el agente aprendió a imitar mi corrección. Tengo los dos modelos: `a2c_sim.pth` (base) y `a2c_dagger.pth` (refinado).

---

# PARTE 2 — Comandos para la demostración en vivo

> Antes de la expo: ten **Gazebo cerrado** y abre 2 terminales. Lanza siempre desde `~/turtlebot3_ws`.

## Preparación (Terminal 1 — Gazebo)
```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_dqn_stage4.launch.py
```
*Espera a que abra la ventana del simulador con el robot y los obstáculos.*

---

## DEMO 1 — Mostrar el agente A2C entrenado (Terminal 2)
```bash
cd ~/turtlebot3_ws
ros2 run turtlebot3_a2c test a2c_sim
```
*Qué decir:* "Este es mi agente A2C de acción continua, ejecutando la política que aprendió. Predice velocidad lineal y angular continuas para llegar a la meta."

---

## DEMO 2 — Entrenamiento A2C en vivo (opcional, Terminal 2)
```bash
cd ~/turtlebot3_ws
ros2 run turtlebot3_a2c train
```
*Qué señalar:* las líneas `Ep ... | reward ... | success/collision` y las `update | L_actor | L_critic | H` (las 3 losses actualizándose). Detén con `Ctrl+C` cuando hayas mostrado unos episodios.

---

## DEMO 3 — DAgger con intervención humana (Terminal 2) ⭐ la principal
```bash
cd ~/turtlebot3_ws
ros2 run turtlebot3_a2c dagger
```
*Confirma que aparezca:* `Modelo base cargado: ...a2c_sim.pth`

**Secuencia para la demo (con la terminal de DAgger seleccionada):**
1. Deja al A2C pilotear solo (modo AUTO). *"Aquí pilotea mi agente A2C."*
2. Pulsa **`i`** → tomas el control. *"Intervengo como experto humano."*
3. Guía el robot con **`w`** (avanzar), **`a`** (izquierda), **`d`** (derecha), **`s`** (parar). *"Se están capturando los pares estado-acción."*
4. Pulsa **`t`** → fine-tuning. *Señala el mensaje:* `Fine-tuning con N pares | loss ...`. *"El agente aprende a imitarme; la loss baja."*
5. Pulsa **`i`** → vuelves a AUTO. *"Ahora valido: el robot se porta mejor en esta zona → aprendió de mi intervención."*
6. Pulsa **`q`** → guarda `a2c_dagger.pth` y sale.

---

## DEMO 4 — Validar el modelo refinado (Terminal 2)
```bash
cd ~/turtlebot3_ws
ros2 run turtlebot3_a2c test a2c_dagger
```
*Qué decir:* "Este es el agente después de DAgger. Comparado con el A2C base, mejora en las zonas donde intervine."

---

## Mostrar los entregables
```bash
ls ~/turtlebot3_ws/a2c_models/
```
*Debe mostrar:* `a2c_sim.pth` (A2C base) y `a2c_dagger.pth` (refinado con DAgger).

---

# Posibles preguntas del profesor (y cómo responder)

- **¿Por qué A2C y no DQN?** → Porque la tarea exige acción continua y DQN solo maneja acciones discretas.
- **¿Dónde está el Actor Gaussiano?** → En `networks.py`: tiene una cabeza para μ y otra para σ.
- **¿Cómo cumples `gym.spaces.Box`?** → En `environment.py`, defino el `action_space` y `observation_space` como `Box`.
- **¿Cómo penalizas los giros?** → En la recompensa resto un término proporcional a `|ω|`.
- **¿Cómo funciona DAgger aquí?** → El A2C pilotea, yo intervengo por teclado, capturo pares (estado, acción) y hago fine-tuning por imitación (MSE).
- **¿Cómo validas que aprende?** → La loss de imitación baja, y en AUTO el robot mejora en las zonas corregidas.
- **¿Y el robot real?** → El mismo código corre en el robot físico (mismos tópicos `/scan`, `/odom`, `/cmd_vel`), en modo `test`, cargando `a2c_dagger.pth`. Esa es la Fase 3.
