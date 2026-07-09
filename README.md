# Growth Dashboards

Aplicación web (Flask) para alojar múltiples dashboards de experimentos de
Growth. La portada es un mosaico de experimentos; cada uno tiene sus vistas
(proyección, seguimiento, …). Pensada para vivir en GitHub y desplegarse en
Render.

La idea central: **no se toca el código para sumar un experimento**. Cada
experimento es una carpeta dentro de `projects/` que respeta una convención;
la app la descubre y la publica sola.

## Estructura

```
growth-dashboards/
├── app.py                  # rutas (genéricas, no conocen ningún proyecto)
├── core/registry.py        # descubre las carpetas de projects/
├── templates/              # base, mosaico (index), shell de dashboard, 404
├── static/css/main.css     # estilo (crema · hueso · gris oscuro · Lato)
├── projects/
│   ├── puesta_en_marcha_ltv/
│   │   ├── meta.json        # ficha: título, subtítulo, vistas, orden
│   │   ├── data/            # datos crudos (Data_2025.csv, Data_2026.csv)
│   │   ├── processor.py     # build() -> {"proyeccion": {...}, "seguimiento": {...}}
│   │   └── templates/
│   │       ├── proyeccion.html
│   │       └── seguimiento.html
│   └── proyecto_demo/        # copia idéntica, solo cambia el nombre de carpeta
├── requirements.txt
├── render.yaml / Procfile / runtime.txt
└── .gitignore
```

## Correr en local

```bash
cd growth-dashboards
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abrir http://127.0.0.1:5000

Para recalcular las métricas de un proyecto sin reiniciar:
añade `?refresh=1` a la URL de una vista.

## Subir a GitHub

```bash
cd growth-dashboards
git init
git add .
git commit -m "Growth Dashboards: estructura inicial + experimento LTV"
git branch -M main
git remote add origin https://github.com/<usuario>/<repo>.git
git push -u origin main
```

## Conectar a Render

1. Render → **New +** → **Web Service** → conecta el repo de GitHub.
2. Render detecta `render.yaml`. Si pide los campos a mano:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Runtime:** Python 3
3. Deploy. Cada `git push` a `main` vuelve a desplegar (autoDeploy).

> Plan Free de Render: el servicio se duerme tras inactividad; la primera
> carga tras dormir tarda unos segundos.

## Agregar un experimento nuevo

1. Copia una carpeta de `projects/` con un nombre nuevo (sin espacios).
2. Edita su `meta.json` (`slug`, `title`, `subtitle`, `views`, `order`).
3. Pon tus datos en `data/`.
4. Ajusta `processor.py` → `build()` para que devuelva el contexto de cada vista.
5. Ajusta las plantillas en `templates/` (o reutiliza las que ya hay).

Commit + push y aparece solo en el mosaico. No se edita `app.py`.

### Contrato de un proyecto

- `meta.json`: al menos `slug`, `title` y `views` (lista de `{slug, label}`).
- `processor.py`: una función `build()` que devuelve un dict cuyas claves son
  los `slug` de las vistas y cada valor es el contexto que recibe la plantilla.
- `templates/<vista>.html`: extiende `dashboard_base.html` y rellena
  `{% block view %}`.

## Gráficos

`core/charts.py` genera gráficos SVG en el servidor (barras y sparklines), sin
librerías de cliente. Se estilizan con las variables CSS del sitio y se animan
por CSS. Cualquier proyecto puede importarlos:

```python
from core.charts import bar_chart, sparkline
```

El partial `templates/_evolucion.html` arma la sección de evolución mensual a
partir de un dict `evol` (rango, gráfico de volumen y sparklines por métrica),
y se incluye desde las vistas con `{% include "_evolucion.html" %}`.

## Sobre el experimento LTV

- **Proyección** (Data_2025): impacto esperado de ampliar topes de LTV, calculado
  sobre el histórico. Métrica destacada: desembolso adicional anual estimado.
  Conteo de casos: 87 elegibles = 84 cerrados + 3 sin contrato (idéntico a las
  celdas "Cantidad de Casos" de la notebook). Se muestran dos tickets: de casos
  con contrato cerrado y del segmento general.
- **Seguimiento** (Data_2026): impacto real desde el 27-mar-2026, con comparación
  esperado vs. real en conversión, ticket y días de cierre.
- Ambas vistas incluyen la **evolución mensual** agrupada por `Periodo de Cierre`.

La lógica de `processor.py` replica la notebook `Puesta_en_Marcha_LTV.ipynb`.

## Acceso / seguridad

El acceso es por **código de un solo uso (OTP) al correo corporativo**:

1. La persona ingresa su correo `@prestamype.com`, que además debe estar en la
   lista de permitidos (`ALLOWED_EMAILS`, correos separados por coma; si no se
   define, aplica la lista por defecto del código).
2. Recibe un PIN de 6 dígitos por correo, válido por 15 minutos (máx. 5
   intentos, reenvío con espera de 60 s).
3. La sesión queda abierta 7 días en una cookie firmada (HttpOnly, Secure en
   producción). "Salir" en la cabecera cierra la sesión.

El PIN no se guarda en el servidor: viaja como HMAC firmado con `SECRET_KEY`,
por lo que el flujo sobrevive a los reinicios del plan free de Render.

Variables de entorno (Render → Environment):

- `SECRET_KEY` — cadena larga y aleatoria (firma sesiones y PINs).
- `ALLOWED_EMAILS` — lista de correos con acceso. Ampliarla = editar esta
  variable; Render reinicia el servicio al guardar, sin tocar código.
- `BREVO_API_KEY` y `SMTP_FROM` — envío de códigos por la API HTTPS de
  Brevo (la vía que funciona en Render, que bloquea SMTP saliente).
  `SMTP_FROM` debe ser un remitente verificado en Brevo.
- Alternativa para hosts con SMTP saliente permitido: `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (y opcional `SMTP_FROM`).

Sin SMTP configurado (desarrollo local), el PIN se imprime en los logs del
servidor para poder probar el flujo.


## Personalización de marca

- **Logo**: reemplaza `static/brand/logo.svg` por el tuyo (mismo nombre de
  archivo). Aparece en la cabecera y en la pantalla de acceso.
- **Imagen de carga**: reemplaza `static/brand/loading.svg`. La animación en
  loop (latido + flotación) la aplica el CSS, así que cualquier imagen que
  pongas quedará animada automáticamente.
- **Paleta**: definida en `static/css/main.css` (`:root`): blanco / blanco
  hueso, verde principal `#00CB75`, verde claro `#B6FFB6` (solo rellenos y
  acentos sobre fondos oscuros) y grises neutros para el texto.

## Pantalla de "waking up" de Render

La página de espera que muestra Render al despertar un servicio del plan free
pertenece al proxy de Render y no se puede rediseñar (aparece antes de que la
app arranque). Dos mitigaciones incluidas:

1. **Keep-alive**: el endpoint público `/salud` responde sin autenticación.
   Configura un monitor gratuito (p. ej. UptimeRobot o cron-job.org) que
   visite `https://<tu-app>.onrender.com/salud` cada 10 minutos y el servicio
   no volverá a dormirse (el plan free incluye 750 h/mes: alcanza para 24/7).
2. **Pantalla de carga propia**: dentro de la app, cualquier navegación que
   tarde más de ~350 ms muestra una capa con tu imagen de
   `static/brand/loading.svg` animada en loop.
