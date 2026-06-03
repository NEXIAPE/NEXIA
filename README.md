# NEXIA — Landing de captación (v3.0)

Landing de conversión para **NEXIA Consulting**, alineada al *Sistema Operativo v3.0*.
Objetivo único: **maximizar reuniones (diagnósticos) agendadas** con negocios que crecieron más rápido que su estructura.

> Implementamos, no aconsejamos.

---

## 1. Qué cambió respecto a la versión anterior (resumen de la auditoría)

La landing anterior estaba construida sobre el posicionamiento **v2** que el propio
Sistema Operativo v3.0 declara obsoleto. Cambios estructurales:

| # | Antes (v2) | Ahora (v3.0) | Por qué |
|---|------------|--------------|---------|
| 1 | "Diagnóstico gratuito para tu PYME" | "Instalamos el sistema operativo que tu negocio necesita para crecer sin depender de su dueño" | "PYME" ancla el precio hacia abajo. v3.0 afila el ICP al arquetipo Roser. |
| 2 | **Precios visibles** (SCAN PRO, bloque de precio) | **Sin precio en toda la página** | Regla de oro v3.0: el precio aparece *solo en la propuesta*. |
| 3 | SCAN FREE / SCAN PRO (dos productos pagos) | Un solo diagnóstico **gratuito con quick wins** | El diagnóstico es el imán de clientes, no un producto. |
| 4 | 4 servicios co-iguales (FLUJO/MOTOR/CEREBRO/CONTROL) | 4 **lentes** del diagnóstico + flagship TRANSFORM + PARTNER | "Un diagnóstico produce un foco, no un menú." |
| 5 | Sin prueba social | **Caso real (Grupo Roser)** con métricas duras | La prueba pesa más que el discurso. |
| 6 | Formspree con fallback "éxito falso", sin agenda | **Formulario → Formspree + CRM → Calendly** real | Capturar el lead *y* agendar la reunión en un solo flujo. |
| 7 | SEO básico | Schema (ProfessionalService, WebSite, FAQPage), OG/Twitter, FAQ, a11y, performance | Credibilidad técnica + tráfico orgánico. |

La auditoría completa se entregó en el chat.

---

## 2. Arquitectura del flujo de leads

```
Landing (index.html)
   │
   ▼
Formulario de calificación  (modal, paso 1)
   │  fan-out en paralelo (no bloquea al usuario)
   ├──────────────▶ Formspree ──▶ Email a admin@nexia.fit
   └──────────────▶ Make webhook ─┬─▶ Google Sheets / Airtable  (CRM: estado LEAD)
                                  └─▶ Seguimiento automático (regla < 2h del Sistema Operativo)
   │
   ▼
Calendly  (modal, paso 2)  ──▶ evento agendado ──▶ Email confirmación + estado "LLAMADA agendada"
   │
   ▼
Tracking: GA4 + Meta Pixel  (lead_start → lead_submit → meeting_booked)
```

**Por qué esta arquitectura** (simplicidad + costo):

- **Formspree** (no un backend propio): la landing es estática → cero servidores, cero mantenimiento. Free tier: 50 envíos/mes; email instantáneo a `admin@nexia.fit`. Si se supera, su plan pago es marginal.
- **Calendly** ya está en el stack de la firma (Sistema Operativo, cap. 09). Embebido inline en el modal: el lead reserva sin salir de la página → maximiza la tasa de reunión agendada.
- **Make** (opcional) conecta el lead al **CRM ligero** (Sheets→Airtable) y dispara el seguimiento que el Sistema Operativo exige ("Responder < 2 h"). Un solo webhook, sin código.
- **El lead se captura ANTES de Calendly**: aunque el usuario no termine de agendar, sus datos ya llegaron por Formspree + Make. Cero leads perdidos.

---

## 3. Puesta en marcha (5 minutos)

Edita el bloque `NEXIA_CONFIG` al final de `index.html`:

```js
const NEXIA_CONFIG = {
  FORMSPREE_ID:  'xxxxxxx',                                  // (1)
  CALENDLY_URL:  'https://calendly.com/nexia/diagnostico-gratuito', // (2)
  MAKE_WEBHOOK:  'https://hook.eu2.make.com/xxxxxxxx',       // (3) opcional
  GA4_ID:        'G-XXXXXXXXXX',                             // (4) opcional
  META_PIXEL_ID: '1234567890'                                // (5) opcional
};
```

1. **Formspree** — crea cuenta en [formspree.io](https://formspree.io) → *New form* → destino `admin@nexia.fit` → copia el ID del endpoint (`formspree.io/f/XXXX`).
2. **Calendly** — crea un *Event Type* "Diagnóstico NEXIA" (30 min) y pega su URL pública. La landing ya prellena nombre/email y aplica los colores de marca.
3. **Make** (opcional) — crea un *scenario* con trigger **Custom Webhook**; conecta módulos *Google Sheets → Add Row* y/o *Airtable → Create Record*; pega la URL del webhook. Campos que llegan: `nombre, empresa, email, whatsapp, tamano_equipo, desafio, origen, fecha`.
4. **GA4** — ID de medición de Google Analytics 4.
5. **Meta Pixel** — ID del píxel de Meta.

> Mientras los placeholders no se reemplacen, la landing **degrada con elegancia**: el formulario muestra el estado "Recibido" y no rompe. Calendly solo aparece cuando hay URL real.

### Eventos de conversión que se disparan

| Evento (GA4) | Meta Pixel | Cuándo |
|---|---|---|
| `lead_start` | `InitiateCheckout` | Se abre el modal |
| `lead_submit` | `Lead` | Se envía el formulario |
| `meeting_booked` | `Schedule` | Se agenda en Calendly |

---

## 4. Optimizaciones incluidas

- **SEO técnico**: `<title>`/description orientados a la categoría, canonical, keywords, robots.
- **Schema markup** (JSON-LD): `ProfessionalService`, `WebSite`, `FAQPage`.
- **Social**: Open Graph + Twitter Card (falta subir `og-image.png` 1200×630).
- **Performance**: preconnect/preload de fuentes, `font-display:swap`, Calendly cargado *on-demand* (solo al llegar al paso 2), favicon SVG inline (0 requests), CSS crítico inline, sin frameworks.
- **Accesibilidad**: roles ARIA, `aria-modal`, foco gestionado, cierre con `Esc`, navegación por teclado, `:focus-visible`, `prefers-reduced-motion`, contraste AA, labels en todos los campos.
- **Mobile-first**: grids colapsables, áreas táctiles ≥ 44px, modal con scroll, sin overflow horizontal.

## 5. Pendientes de marca (assets)

- [ ] Subir `og-image.png` (1200×630) para previews en redes.
- [ ] Reemplazar los 5 valores de `NEXIA_CONFIG`.
- [ ] (Opcional) Verificar dominio en Formspree para quitar el branding del email.
