# Wave Picking para almacenes

Proyecto integrador de **Algoritmos II**. Modela un warehouse, organiza pedidos en waves y simula cómo varios pickers recorren el almacén para recoger productos y llevarlos a zonas de despacho. Incluye una interfaz gráfica para generar o editar escenarios, ejecutar la simulación y guardar o reanudar partidas.

## Requisitos

- Python instalado.
- Las dependencias listadas en [`proyeto_integrador/requirements.txt`](proyeto_integrador/requirements.txt).
- Windows, Linux o macOS. La interfaz gráfica requiere un entorno con soporte para Pygame.

## Instalación

Desde la carpeta raíz del repositorio, creá y activá un entorno virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalá las dependencias:

```powershell
python -m pip install -r .\proyeto_integrador\requirements.txt
```

En macOS o Linux, la activación del entorno virtual es:

```bash
source .venv/bin/activate
```

## Ejecutar la aplicación

Desde la raíz del repositorio:

```powershell
python .\proyeto_integrador\visualization\Main.py
```

Al iniciar sin argumentos, la aplicación restaura el autoguardado más reciente, si existe. Si no hay una partida guardada, genera un escenario inicial.

Para abrir un escenario JSON y comenzar una simulación nueva:

```powershell
python .\proyeto_integrador\visualization\Main.py --escenario ".\proyeto_integrador\domain\escenario_basico.json"
```

También podés pasar una ruta absoluta, por ejemplo:

```powershell
python .\proyeto_integrador\visualization\Main.py --escenario "$env:USERPROFILE\Downloads\mi_escenario.json"
```

## Uso de la interfaz

### Controles de simulación

- **A*** o **Dijkstra**: selecciona el algoritmo para buscar caminos.
- **Orden**, **Cercanía** o **Zonas**: selecciona la estrategia para ordenar los productos de cada viaje.
- **Iniciar**, **Pausar**, **Continuar**, **Reiniciar** y **Paso**: controlan el avance de la simulación.
- **− / +**: reducen o aumentan la velocidad de animación.
- **Generar escenario**: abre las pestañas Automático y Manual.
- **Cargar escenario / Guardar escenario**: abren o guardan un diseño de warehouse.
- **Cargar partida / Guardar partida**: reanudan o guardan el progreso de una simulación.

Atajos disponibles durante la simulación: `Espacio` para iniciar, pausar o continuar; `N` para un paso; `R` para reiniciar; `+` y `-` para la velocidad; `I` para mostrar u ocultar intersecciones.

### Generar escenarios

En **Automático** se configuran estantes, pasillos, productos, pedidos, pickers, ubicación de productos y el peso máximo de cada despacho. El límite inicial es **500 kg por zona** y se puede cambiar. La vista previa representa el warehouse generado con esos parámetros.

En **Manual** se dibujan los elementos sobre el mapa. Al soltar una zona de despacho se puede ingresar su peso máximo individual; si se cancela ese cuadro, la zona conserva el valor inicial de 500 kg. El editor valida el mapa antes de permitir usarlo.

Atajos del editor Manual: `1` rack, `2` despacho, `3` puerta, `4` pasillo, `5` picker, `6` borrar y `7` producto. Para cambiar el sentido del pasillo se usan `N`, `S`, `E`, `O` o `A` (ambos sentidos); `Ctrl+Z` deshace y `V` valida el mapa.

### Cómo se asignan las waves y los pickers

Una wave **puede ser atendida por varios pickers**. El asignador entrega viajes a los pickers disponibles y vuelve a asignar trabajo a medida que quedan libres. La capacidad de carga de cada picker limita el peso de su viaje.

Cada zona de despacho tiene su propio límite acumulado. El peso de los viajes ya asignados se reserva para evitar sobrepasar la capacidad entre pickers que trabajan al mismo tiempo. Cuando se agota la capacidad disponible, la zona deja de recibir viajes durante esa simulación; los que ya estaban asignados pueden terminar. Otras zonas con capacidad todavía pueden usarse.

Si quedan productos que no se pueden asignar, la simulación completa primero el trabajo posible, marca las waves afectadas como incompletas y muestra un aviso con los productos pendientes.

## Escenarios JSON

El archivo de escenario contiene la configuración necesaria para crear una simulación nueva. Sus secciones principales son:

- `warehouse`: dimensiones, puertas, zonas de despacho, racks y pasillos.
- `pickers`: identificador, posición inicial y capacidad de carga en kg.
- `productos`: producto, rack, ubicación, stock y peso por unidad.
- `pedidos`: líneas con identificador de producto y cantidad.
- `configuracion`: límites de pedidos y productos por wave.

Cada zona de despacho debe incluir `peso_max_kg`. El generador automático y el editor manual exportan ese valor en el JSON. El archivo de ejemplo está en [`proyeto_integrador/domain/escenario_basico.json`](proyeto_integrador/domain/escenario_basico.json); también hay escenarios de experimentación en [`proyeto_integrador/escenarios_experimentacion/`](proyeto_integrador/escenarios_experimentacion/).

La aplicación valida los escenarios al cargarlos. Si un producto no tiene acceso al despacho, se informa y se excluye del trabajo que se asigna.

## Escenario y partida

| Archivo | Qué guarda | Qué ocurre al cargarlo |
| --- | --- | --- |
| **Escenario JSON** | Mapa, zonas, productos, pedidos, pickers iniciales y configuración | Se crea una simulación nueva desde el comienzo |
| **Partida JSON** | El escenario más el estado actual: tick, waves, pickers, stock, capacidad ocupada y velocidad | Se reanuda la simulación guardada |

Usá **Cargar escenario** para un JSON de escenario y **Cargar partida** para un JSON creado con **Guardar partida**. Si se elige el tipo equivocado, la aplicación muestra un aviso.

Además de las partidas guardadas manualmente, la aplicación conserva automáticamente la última partida en:

- Windows: `%LOCALAPPDATA%\WavePicking\ultima_partida.json`
- Linux/macOS: `$XDG_STATE_HOME/WavePicking/ultima_partida.json`; si `XDG_STATE_HOME` no está definido, `~/.local/state/WavePicking/ultima_partida.json`.

## Estructura del código

```text
proyeto_integrador/
├── domain/             # Entidades y validaciones del warehouse
├── simulation/         # Generación, waves, caminos, asignación, simulación y persistencia
├── visualization/      # Aplicación Pygame, mapa, paneles y editor de escenarios
├── escenarios_experimentacion/  # JSON para pruebas de experimentación
├── MedirCargaEscenarioGrande.py # Medición de validación y asignación
└── requirements.txt    # Dependencias Python
```

Módulos relevantes:

- `domain/Warehouse.py`: modelo del almacén y reglas de colocación.
- `simulation/Scenario.py`: generación y validación de escenarios.
- `simulation/Recorridos.py`, `Navegation.py` y `PlanificadorViajes.py`: búsqueda de caminos y planificación de viajes.
- `simulation/AsignadorPickers.py`: asignación de viajes y control de peso de pickers y despachos.
- `simulation/Simulation.py`: avance de la simulación y estado de pickers y waves.
- `simulation/Persistence.py`: lectura y escritura de escenarios y partidas JSON.
- `visualization/Main.py`: punto de entrada de la aplicación.
- `visualization/GeneradorPantalla.py` y `EditorEsc.py`: generación automática y edición manual de mapas.

La carpeta `backup_archivos_inutiles/` contiene versiones archivadas y no forma parte de la ejecución normal.

## Medición de carga

Desde la raíz del repositorio podés ejecutar los casos pequeños del script de medición:

```powershell
python .\proyeto_integrador\MedirCargaEscenarioGrande.py small
python .\proyeto_integrador\MedirCargaEscenarioGrande.py small-greedy
```

Para medir un escenario JSON propio:

```powershell
python .\proyeto_integrador\MedirCargaEscenarioGrande.py "$env:USERPROFILE\Downloads\mi_escenario.json"
```

El modo `heavy-repeat` ejecuta tres mediciones del mismo escenario. El modo `all` compara casos chicos y uno pesado:

```powershell
python .\proyeto_integrador\MedirCargaEscenarioGrande.py heavy-repeat "$env:USERPROFILE\Downloads\mi_escenario.json"
python .\proyeto_integrador\MedirCargaEscenarioGrande.py all "$env:USERPROFILE\Downloads\mi_escenario.json"
```
