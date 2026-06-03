# Rastreador STOCK Act (v1) — guía para principiantes

Proyecto educativo en Python que **rastrea operaciones bursátiles divulgadas
públicamente** por legisladores de EE.UU. bajo la **STOCK Act**. Está diseñado
para consolidar **varias fuentes** de forma **modular**: cada fuente es un
"conector" independiente que puedes encender o apagar sin romper el resto.

> ⚠️ **Esto NO es asesoría financiera.** El programa solo describe e informa
> datos **públicos**. No da recomendaciones de compra/venta. Además, los datos
> tienen un **desfase legal de hasta ~45 días** (ver sección de advertencias).

---

## 0. ¿Qué hace, en una frase?

> Descarga lo que los legisladores reportaron, junta las fuentes, quita
> duplicados, lo guarda en una base de datos y te genera un **informe diario
> en texto**: divulgaciones nuevas, top 10 de tickers (30 días) y desglose por
> sector.

En la **versión 1 solo está activa la Cámara de Representantes (House)**. El
Senado y un agregador externo ya están programados como "esqueletos" pero
**desactivados**, listos para encenderse más adelante (ver sección 6).

---

## 1. La arquitectura (cómo está organizado)

```
                 ┌─────────────────────────────────────────────┐
                 │                  main.py                     │
                 │            (el orquestador)                  │
                 └───────────────────┬─────────────────────────┘
                                     │ pide datos a las fuentes ACTIVAS
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
 connectors/house_clerk.py   connectors/senate_efd.py   connectors/external_aggregator.py
   ✅ ACTIVO (v1)               ⛔ desactivado              ⛔ desactivado (plantilla)
        │                            │                            │
        └──────────── todos devuelven el MISMO formato: `Disclosure` ───────────┘
                                     │
                                     ▼
                       consolidation.py   ← junta todo y quita duplicados/enmiendas
                                     │
                                     ▼
                          storage.py (SQLite)   ← guarda y detecta "lo nuevo"
                                     │
                                     ▼
                          report.py   ← informe diario en texto
```

**Archivos clave** (todos comentados en español):

| Archivo | Qué hace |
|---|---|
| `config.py` | **El único archivo que sueles tocar.** Enciende/apaga fuentes y ajustes. |
| `models.py` | Define el "formato común" (`Disclosure`) que hablan todas las fuentes. |
| `connectors/base.py` | El "molde" que toda fuente debe cumplir. |
| `connectors/house_clerk.py` | Conector de la Cámara (**activo**). |
| `connectors/senate_efd.py` | Conector del Senado (**desactivado**, esqueleto). |
| `connectors/external_aggregator.py` | Hueco para un agregador externo (**desactivado**). |
| `consolidation.py` | Junta fuentes y elimina duplicados/enmiendas. |
| `storage.py` | Base de datos SQLite + detección de novedades. |
| `report.py` | Genera el informe diario. |
| `main.py` | Lo que ejecutas. |

**¿Por qué modular?** Porque cada conector traduce su fuente al formato común
`Disclosure`. El resto del programa solo entiende `Disclosure`, así que puedes
**añadir o quitar fuentes** sin tocar la consolidación, la base de datos ni el
informe.

---

## 2. Requisitos previos

- **Python 3.9 o superior.** Compruébalo en tu terminal:
  ```bash
  python3 --version
  ```
  Si no lo tienes, descárgalo de https://www.python.org/downloads/ .

---

## 3. Instalación paso a paso (primera vez)

> Si nunca usaste una terminal: en **macOS** abre "Terminal"; en **Windows**
> abre "PowerShell"; en **Linux** abre tu terminal favorita.

**1) Entra a la carpeta del proyecto:**
```bash
cd stockact_tracker
```

**2) Crea un "entorno virtual"** (una cajita aislada para las librerías de este
proyecto, para no ensuciar tu Python global):
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```
Sabrás que está activo porque verás `(.venv)` al inicio de la línea.

**3) Instala las dependencias:**
```bash
pip install -r requirements.txt
```
(Instala `requests` para descargar y `pdfplumber` para leer los PDF.)

---

## 4. Pruébalo SIN internet (recomendado antes que nada)

Antes de salir a internet, confirma que todo el "esqueleto" funciona con datos
de ejemplo:
```bash
python main.py --self-test
```
Deberías ver cómo **elimina 1 duplicado**, **fusiona 1 enmienda** y genera un
informe. Si esto funciona, el proyecto está bien instalado. 🎉

> El self-test guarda en la misma base de datos (`stockact.db`). Si quieres
> empezar de cero antes de la corrida real, borra ese archivo:
> `rm stockact.db` (macOS/Linux) o `del stockact.db` (Windows).

---

## 5. Ejecútalo de verdad (con la Cámara, fuente activa en v1)

```bash
python main.py
```

Qué pasa por dentro:
1. Descarga el índice anual de la Cámara (un ZIP con un XML).
2. Filtra los **PTR** (Periodic Transaction Reports = compras/ventas).
3. En la **primera corrida** procesa lo disponible; en las siguientes, **solo
   lo presentado desde la última vez** (incremental).
4. Por cada PTR, descarga su PDF e intenta extraer las transacciones.
5. Consolida, guarda en SQLite y genera el informe en `output/`.

Otros comandos útiles:
```bash
python main.py --report-only   # regenera el informe con lo que ya hay guardado
```

### ⚠️ Límite honesto del parseo de PDF
- Los PTR presentados **electrónicamente** (lo más común hoy) son PDF con texto
  y **se parsean bien** (sacamos ticker, tipo, monto, fecha).
- Los PTR **escaneados o a mano** son imágenes: **no se pueden leer**. En ese
  caso, la presentación **igual aparece** en el informe como "nueva
  divulgación", pero **sin ticker ni monto** (marcada como "no parseable").
- Por eso, el "top de tickers" y el "desglose por sector" reflejan solo las
  transacciones que **sí** se pudieron leer. Es una limitación real de la
  fuente, no un error del programa.

---

## 6. Activar fuentes adicionales (cuando estés listo)

El diseño por etapas es a propósito: **haz que la v1 (solo Cámara) funcione de
punta a punta antes de sumar complejidad.** Cuando quieras más fuentes:

### 6.1 Activar el Senado (portal EFD)
1. En `config.py`, cambia `"senate": {"enabled": False}` a `True`.
2. Abre `connectors/senate_efd.py`. Verás que **hoy devuelve vacío a propósito**
   (es un esqueleto). El Senado es más difícil que la Cámara porque:
   - No publica un ZIP/XML anual descargable.
   - Su portal (`efdsearch.senate.gov`) exige **aceptar términos** en un
     formulario antes de buscar (crea una sesión con cookies/CSRF).
   - Los resultados son HTML/JSON paginado; cada PTR es un documento aparte.
3. Implementa los pasos marcados con `TODO` en ese archivo (aceptar términos →
   buscar PTRs paginados → mapear cada fila a `Disclosure`). El resto del
   programa (consolidación, BD, informe) **ya lo soporta** sin cambios.

### 6.2 Activar un agregador externo
1. Elige un proveedor que **permita** tu uso (lee su licencia y términos).
2. En `config.py`, pon `"aggregator": {"enabled": True, "api_key": "TU_CLAVE"}`.
3. En `connectors/external_aggregator.py`, implementa la llamada a su API y
   mapea su JSON a `Disclosure` (hay un esqueleto con `TODO`).

> Como **todas** las fuentes devuelven el mismo `Disclosure`, la consolidación
> detectará y eliminará automáticamente las operaciones que aparezcan
> repetidas entre la Cámara, el Senado y el agregador.

---

## 7. Programar la ejecución diaria (cron job)

Primero asegúrate de que `python main.py` funciona a mano. Luego automatízalo.

### 🐧 Linux / 🍎 macOS — con `cron`
1. Haz el script ejecutable (una sola vez):
   ```bash
   chmod +x scripts/run_daily.sh
   ```
2. Abre el editor de cron:
   ```bash
   crontab -e
   ```
3. Añade esta línea para correr **todos los días a las 8:00 a. m.**
   (reemplaza `/RUTA/COMPLETA` por la ruta real; obtenla con `pwd` dentro de la
   carpeta del proyecto):
   ```cron
   0 8 * * * /RUTA/COMPLETA/stockact_tracker/scripts/run_daily.sh
   ```
   - `0 8 * * *` significa "minuto 0, hora 8, todos los días". Cambia la hora a
     gusto. Útil: https://crontab.guru para entender el formato.
4. Guarda y cierra. Los logs quedan en `output/cron-FECHA.log`.

> 🍎 **macOS**: la primera vez, el sistema puede pedir permiso para que `cron`
> acceda a archivos. Acéptalo en *Ajustes → Privacidad y seguridad*.

### 🪟 Windows — con el Programador de tareas
1. Abre **"Programador de tareas"** (Task Scheduler).
2. *Crear tarea básica…* → nombre: `Rastreador STOCK Act`.
3. Desencadenador: **Diariamente**, elige la hora (ej. 8:00 a. m.).
4. Acción: **Iniciar un programa** y selecciona el archivo:
   `...\stockact_tracker\scripts\run_daily.bat`
5. Finaliza. (Opcional: en *Propiedades* marca "Ejecutar tanto si el usuario
   inició sesión como si no".) Los logs quedan en `output\cron-FECHA.log`.

---

## 8. ⚠️ Advertencias importantes (léelas)

### 8.1 No es asesoría financiera
El proyecto es **descriptivo e informativo**. No genera recomendaciones de
compra/venta. Las decisiones de inversión son tuyas y bajo tu responsabilidad.

### 8.2 Desfase legal de hasta ~45 días
La STOCK Act obliga a reportar las operaciones **dentro de un plazo** (a más
tardar ~30–45 días desde la transacción). Por eso, **lo que ves nunca es en
tiempo real**: puede tener semanas de retraso respecto a la operación real.

### 8.3 Rate limits y buen comportamiento
- Los servidores oficiales **bloquean** a clientes que piden demasiado rápido
  o que no se identifican (verás errores **HTTP 403/429**).
- Este proyecto ya: (a) envía un `User-Agent` identificable, (b) espera
  `REQUEST_DELAY_SECONDS` (2s) entre peticiones y (c) limita cuántos PDF baja
  por corrida (`max_pdf_downloads`). **Si te bloquean, sube esos valores** en
  `config.py`, no los bajes.
- Ejecuta **una vez al día**, no en bucle.

### 8.4 Términos de uso de cada fuente (revísalos tú mismo)
- **Cámara (House Clerk)** — `disclosures-clerk.house.gov`: datos públicos.
  Aun así, respeta su disponibilidad y no satures el servidor.
- **Senado (EFD)** — `efdsearch.senate.gov`: **exige aceptar un acuerdo de uso**
  antes de buscar. Léelo y cúmplelo si activas ese conector.
- **Agregador externo**: cada proveedor tiene **su propia licencia**, cuotas y,
  a veces, **restricciones de redistribución**. Léela antes de usar sus datos.

> Los términos y formatos de las fuentes **pueden cambiar**. Si un conector deja
> de funcionar, probablemente la fuente cambió su sitio/formato.

---

## 9. Solución de problemas (FAQ rápida)

| Síntoma | Causa probable / solución |
|---|---|
| `ModuleNotFoundError: requests` | No instalaste dependencias: `pip install -r requirements.txt` (con el `.venv` activo). |
| El informe no muestra tickers | Los PTR de esa tanda eran escaneados, o `pdfplumber` no está instalado. |
| `HTTP 403` o `429` | Te limitaron. Sube `REQUEST_DELAY_SECONDS` y baja `max_pdf_downloads` en `config.py`. |
| Quiero empezar de cero | Borra `stockact.db`. |
| cron no corre | Usa **rutas absolutas** en el crontab y revisa `output/cron-*.log`. |

---

## 10. Estructura de carpetas

```
stockact_tracker/
├── README.md                 ← esta guía
├── requirements.txt          ← dependencias
├── config.py                 ← ENCIENDE/APAGA fuentes y ajustes
├── main.py                   ← lo que ejecutas
├── models.py                 ← formato común (Disclosure)
├── consolidation.py          ← junta fuentes + quita duplicados
├── storage.py                ← SQLite + "solo lo nuevo"
├── report.py                 ← informe diario
├── sectors.py                ← ticker → sector
├── httpclient.py             ← descargas con buenos modales
├── connectors/
│   ├── base.py               ← molde común
│   ├── house_clerk.py        ← ✅ Cámara (activo)
│   ├── house_ptr_parser.py   ← lee transacciones de los PDF
│   ├── senate_efd.py         ← ⛔ Senado (esqueleto)
│   └── external_aggregator.py← ⛔ agregador (plantilla)
├── samples/sample_FD.xml     ← XML de ejemplo para entender el formato
├── scripts/
│   ├── run_daily.sh          ← cron en macOS/Linux
│   └── run_daily.bat         ← Task Scheduler en Windows
└── output/                   ← informes y logs (se crean al ejecutar)
```
