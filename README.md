# 📦 Sistema de Wave Picking para Almacenes (Warehouse)

Proyecto desarrollado para la materia **Algoritmos II**. Consiste en un sistema de simulación y gestión de preparación de pedidos mediante la estrategia de *Wave Picking*, implementando estructuras de datos avanzadas, algoritmos de ruteo y una interfaz de visualización interactiva en Python.

---

## 🚀 Características Principales

- **Modelado de Espacios:** Representación cartesiana del almacén con control de racks, puertas de entrada/salida, zonas de despacho y pasillos con sentidos de circulación restringidos.
- **Gestión de Olas (*Wave Picking*):** Agrupación inteligente de pedidos según prioridades, restricciones de peso, capacidad de carga de los *pickers* y cercanía espacial.
- **Algoritmos de Ruteo (*Pathfinding*):** Cálculo de caminos óptimos para los operarios respetando las restricciones de movilidad del almacén.
- **Simulación Multi-picker:** Ejecución visual interactiva paso a paso con control de colisiones y resolución de conflictos de tráfico.
- **Persistencia:** Carga y guardado de escenarios complejos mediante archivos estructurados.
- **Análisis y Comparación:** Métricas de distancia recorrida, nodos visitados y tiempos de ejecución entre diferentes estrategias algorítmicas.

---

## 📂 Estructura del Proyecto

```text
tp_integrador_algoll/
│
├── proyecto_integrador/
│   ├── domain/               # Modelos de dominio (Warehouse, Productos, Pedidos, Waves)
│   ├── simulation/           # Lógica general de la simulación
│   ├── simulationV/          # Componentes de la interfaz visual e interactiva
│   ├── visualization/        # Renderizado gráfico del almacén y operarios
│   ├── pathFinding.py        # Algoritmos de búsqueda de caminos
│   ├── routePlaning.py       # Planificación de rutas para las waves
│   ├── validation.py         # Validaciones de consistencia del escenario
│   ├── Parser.py             # Procesamiento de archivos de configuración
│   └── Persistence.py        # Manejo de guardado y carga de escenarios
│
├── .gitignore
├── requirements.txt
└── README.md