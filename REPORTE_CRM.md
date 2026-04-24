# 📋 Reporte CRM HECORP — Estado actual

> **Fecha:** 2026-04-24
> **Versión productiva:** commit `f6c833d` (rama `main`, GitHub `hecorp22/appHecorpCom`)
> **Stack:** FastAPI + SQLAlchemy + PostgreSQL + Jinja2 + Tailwind + Leaflet · Docker Compose
> **Dominio:** https://hecorp.com.mx

---

## 🗺️ Mapa global del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HECORP CRM (FastAPI)                         │
├──────────────────┬──────────────────┬──────────────────┬────────────┤
│  COMERCIAL       │  OPERACIÓN       │  REPARTOS        │  CORE      │
│  (Aleaciones)    │  (Producción)    │  (Logística)     │            │
├──────────────────┼──────────────────┼──────────────────┼────────────┤
│ • Clientes       │ • Pedidos        │ • Choferes       │ • Auth JWT │
│ • Proveedores    │ • Envíos         │ • Clientes ruta  │ • Usuarios │
│ • Ctas. Prov.    │ • Tracking       │ • Jornadas       │ • Roles    │
│ • Cotizaciones   │   público        │ • Entregas       │ • Logs     │
│ • Cot. PDF       │ • KPIs           │ • GPS chofer     │ • Métricas │
│ • Email cot.     │ • Export CSV     │ • Foto + firma   │ • CFDI/SAT │
│                  │ • Dashboard      │ • Ticket PDF     │ • Agenda   │
│                  │                  │ • Tracking pub.  │ • Nómina   │
│                  │                  │ • Mapa + rutas   │ • i18n ES  │
└──────────────────┴──────────────────┴──────────────────┴────────────┘
                  │                    │
                  └─→ SMS Twilio  ←────┘
                  └─→ Email Resend ←───┘
                  └─→ Telegram bot ←───┘
```

---

## 1. 🏠 Núcleo · autenticación, usuarios y roles

| Endpoint | Función |
|---|---|
| `POST /login` / `POST /logout` | Sesión con cookie `access_token` (JWT) |
| `GET /admin/users` | CRUD de usuarios (sólo `superuser`) |
| Roles | `superuser`, `admin`, `cliente`, `proveedor` |
| Seguridad | bcrypt, JWT 7 días, middleware `RequestContextMiddleware`, rate-limits, CORS por env |
| Auditoría | Cada acción sensible va a `audit_event` (logs estructurados) |

**Modelos:** `User`, `AuditEvent`
**Plantillas:** `login.html`, `users_admin.html`, `dashboard.html`

---

## 2. 💼 Comercial — Clientes, proveedores, cotizaciones

### 2.1 Clientes (Aleaciones)
- Catálogo de clientes con RFC, contacto, dirección, status
- `GET /admin/clients` con búsqueda y paginación
- Modelo: `Client` · Plantilla: `client_admin.html`

### 2.2 Proveedores y cuentas bancarias
- Catálogo de proveedores con sus **cuentas bancarias** (multi-cuenta por proveedor)
- `GET /admin/providers`
- Modelos: `Provider`, `ProviderAccount` · Plantilla: `provider_admin.html`

### 2.3 Cotizaciones
- Crear, editar, listar, exportar cotizaciones con líneas de producto, IVA, totales
- **PDF profesional con membrete HECORP** (`quotation_pdf.py`)
- **Envío por correo** vía Resend con PDF adjunto (`email_service.send_quotation_email`)
- `GET /admin/quotations` con búsqueda por folio/cliente/status
- Folios automáticos `COT-YYYY-NNNN`
- Modelo: `Quotation` · Plantilla: `quotations_admin.html`

### 2.4 Notificaciones automáticas
- 📩 Al crear cotización → SMS al admin (`+522712120182`)
- 📩 Al crear pedido → SMS al admin
- 📩 Al crear envío → SMS al admin
- ⚠️ Twilio "from" pendiente de configurar (te avisé que lo dejara por hoy)

---

## 3. 🏭 Operación — Pedidos y envíos de Aleaciones

### 3.1 Pedidos (`Order`)
- Conversión cotización → pedido en un click
- Estados: `borrador`, `confirmado`, `produccion`, `listo`, `enviado`, `entregado`, `cancelado`
- Folios `PED-YYYY-NNNN`
- `GET /admin/orders` con filtros por status/cliente

### 3.2 Envíos (`Shipment`)
- Cada pedido genera un envío con **carrier**, **número de guía**, link de tracking del transportista
- **Folio único** + **token público** para tracking
- Estados: `creado`, `en_transito`, `entregado`, `incidencia`
- Página pública `GET /track/{token}` para que el cliente vea su envío sin login
- `GET /admin/shipments` para gestión

### 3.3 Observabilidad / KPIs / Export
- `GET /admin/observability`: logs en vivo, métricas (Prometheus instrumentation)
- `GET /admin/dashboard`: KPIs (cotizaciones del mes, pedidos abiertos, envíos en tránsito)
- `GET /admin/export/*`: CSV de cotizaciones, pedidos, envíos

---

## 4. 🚚 Repartos — Monitoreo de rutas (NUEVO, hoy)

> Módulo independiente del de Envíos. Pensado para repartos diarios:
> tortillería, víveres, paquetería local, lo que sea con **chofer + cliente + GPS**.

### 4.1 Catálogos
- **Choferes** (`delivery_drivers`): nombre, tel, placas, vehículo, status activo, **token de tracking** propio
- **Clientes de reparto** (`delivery_customers`): negocio, encargado, dirección, lat/lng, referencia, kind (cliente/proveedor)

### 4.2 Operación diaria
- **Jornadas** (`delivery_runs`): un día de ruta. Folio `RUN-YYYY-NNNN`. Asigna chofer y opcionalmente una ruta trazada en mapa. Status: `programada → en_curso → completada` (o `incidencia/cancelada`). Contadores `total/completed`.
- **Entregas** (`deliveries`): cada parada. Folio `ENT-YYYY-NNNN`. Tiene cliente, chofer, orden de parada, ventana de horario, ETA, status, monto, ticket #, factura URL, mensaje de entrega, reporte, código de incidencia. Detección automática de retraso (`is_late`).

### 4.3 Dashboard admin (`/delivery`)
- 📊 **KPIs en vivo**: jornadas hoy / entregas hoy / entregadas / **con retraso**
- 🗺 **Mapa Leaflet** color-coded:
  - 🟡 pendiente · 🔵 en ruta · 🟢 entregada · 🔴 retrasada · ⚪ cancelada
  - 🚚 marcadores **en vivo** de los choferes (cyan = ping reciente, gris = sin pings)
- 📝 Formularios para crear chofer / cliente / jornada / entrega
- 🔘 Botones por entrega: En ruta, Entregar, Fallida, **PDF**, Tracking público
- 🔄 Auto-refresh: 30 s entregas, 60 s KPIs

### 4.4 PWA del chofer (`/driver/{token}`)
- Sin login (usa solo su token único)
- Lista solo **sus** entregas de hoy con: cliente, dirección, referencia, producto
- Botones grandes táctiles: 📞 llamar · 🧭 navegar (Google Maps) · En ruta / Entregar / Fallida
- 📍 **GPS en vivo** (botón "activar"): manda `lat/lng/speed/accuracy/heading` cada 5–15 s
- ✍️ **Firma del cliente** con el dedo (canvas HTML5)
- 📷 **Foto** desde la cámara del celular
- 💬 Modal con mensaje al cliente, reporte de cierre, código de incidencia

### 4.5 Tracking público (`/track/d/{code}`)
- Página tipo "Uber Eats" para mandar al cliente por WhatsApp/SMS
- Estado, ETA, chofer, vehículo, mapa con marcador, foto y firma cuando se entregó

### 4.6 Notificaciones automáticas
- 📱 Al crear entrega → SMS al admin
- 📱 Cuando chofer marca **en_ruta** → SMS al cliente: "Tu pedido va en camino"
- 📱 Cuando chofer marca **entregado** → SMS al cliente: "Pedido entregado, gracias"
- ⚠️ Si entrega marca `fallida/reprogramada` → alerta al admin

### 4.7 Documento PDF de entrega
- `GET /api/delivery/{id}/pdf` (admin) → ticket profesional con:
  cliente, chofer, productos, monto, mensaje, reporte de cierre, foto y firma embebidas

---

## 5. 🗺️ Rutas y mapas

| Función | Endpoint |
|---|---|
| Trazado interactivo (clic en mapa, drag&drop, geocoder, OSRM routing) | `GET /maps` |
| Cálculo de **distancia / duración / ETA** automático | UI |
| Búsqueda de POI / direcciones (Nominatim) | UI |
| Guardar ruta a BD (geojson + km + min) | `POST /api/rutas` |
| CRUD admin de rutas | `GET /rutas` · `app/templates/rutas_admin.html` |

---

## 6. 📅 Otros módulos del sistema

| Módulo | Ruta | Estado |
|---|---|---|
| **Agenda** | `/agenda` | ✅ funcional (eventos, calendar) |
| **Nómina** | `/payroll` | ✅ funcional (cálculo, recibos) |
| **CFDI / SAT** | `/cfdi` | ✅ parser de XML CFDI 4.0 |
| **Reconocimiento facial** | `/face` | ✅ (acceso/asistencia) |
| **Bot Telegram** | webhook | ✅ comandos básicos |
| **Avisos legales** | `/privacy`, `/terms` | ✅ públicos |

---

## 7. 🗄️ Base de datos (PostgreSQL · `hecorp_schema`)

```
users                  · usuarios y roles
audit_event            · auditoría
clients                · clientes Aleaciones
providers              · proveedores
provider_accounts      · cuentas bancarias proveedor
quotations             · cotizaciones + líneas
orders                 · pedidos + líneas
shipments              · envíos con tracking
rutas                  · rutas trazadas en mapa
delivery_drivers       · choferes (con last_lat/lng/seen_at/track_token)
delivery_customers     · clientes de reparto
delivery_runs          · jornadas de reparto
deliveries             · entregas individuales (foto/firma/ticket)
delivery_driver_pings  · histórico GPS de choferes
cfdi                   · CFDI emitidos/recibidos
eventos                · agenda
visits                 · accesos faciales
```

---

## 8. ✅ Lo que YA funciona end-to-end

- [x] Login + JWT + roles
- [x] CRUD clientes / proveedores / cotizaciones / pedidos / envíos
- [x] Cotización PDF con membrete HECORP
- [x] Envío de cotización por correo (Resend) — **falta `RESEND_API_KEY` en prod**
- [x] Tracking público de envíos `/track/{token}`
- [x] Trazado de rutas en mapa con OSRM, ETA, guardado a BD
- [x] Dashboard de monitoreo de entregas con mapa vivo
- [x] PWA chofer con GPS, firma, foto
- [x] PDF de ticket de entrega con foto y firma
- [x] SMS automáticos a admin y cliente (Twilio) — **falta `from` válido**
- [x] Webhook Telegram + comandos
- [x] Agenda, nómina, CFDI, reconocimiento facial

## 9. ⚠️ Pendientes inmediatos

1. **Configurar `TWILIO_FROM`** con número aprobado para México (lo dejaste para después)
2. **Configurar `RESEND_API_KEY`** en `.env` de producción
3. **Verificar dominio** en Resend para que no caiga en spam
4. (Opcional) Subir avatar / logo más grande en PDFs

---

## 10. 🚀 Lo que podemos agregar

### 🥇 Prioridad alta — completar el módulo Repartos

1. **Optimización TSP de rutas** — Algoritmo que ordena las paradas por cercanía minimizando km totales. Botón "Optimizar ruta" en el admin: pasa de "ir saltando" a una secuencia eficiente.
2. **Alertas automáticas** — Cron cada 5 min:
   - Si un chofer no manda GPS por > 15 min durante jornada → SMS al admin
   - Si una entrega lleva > 30 min retrasada → SMS al admin + cliente
3. **WebSocket / SSE en lugar de polling** — Mapa que se actualiza al instante cuando llega un ping (hoy lo hace por polling cada 30s)
4. **App PWA instalable** — `manifest.json` + service worker para que el chofer la instale como app y funcione offline (cache de entregas del día)
5. **Historial completo del chofer** — Reporte semanal/mensual: km, entregas, % éxito, % retraso, mapa de calor de zonas

### 🥈 Prioridad media — extender el CRM

6. **Inventario / almacén** — productos, stock, mínimo, salida cuando se entrega, alertas de reorden
7. **Cobranza** — cuentas por cobrar, cliente moroso, recordatorios automáticos por SMS/email
8. **Pagos en línea** — Stripe / Mercado Pago / Conekta; QR en el ticket de entrega para pagar
9. **Facturación CFDI 4.0 emitida** — hoy parsean XMLs, falta emitir desde cotización/entrega
10. **Reportes ejecutivos** — gráficas mensuales, top clientes, márgenes, rentabilidad por ruta
11. **Multi-empresa / multi-sucursal** — si HECORP abre otra unidad

### 🥉 Calidad de vida

12. **Modo oscuro / claro** consistente en todo el dashboard
13. **App móvil nativa** (React Native) para el admin (notificaciones push)
14. **Exportar a Excel** además de CSV
15. **Plantillas de mensaje WhatsApp Business** — confirmaciones, recordatorios
16. **Backups automáticos diarios** de Postgres a S3
17. **Sentry** para errores en producción
18. **Tests E2E con Playwright** del flujo cotización → pedido → envío → entrega

### 🌟 Nicho HECORP

19. **Integración con báscula / etiquetadora** para Aleaciones
20. **Códigos QR únicos por entrega** — el chofer escanea al llegar, evita confundir paradas
21. **Firma electrónica con valor legal (FIEL)** para cotizaciones grandes
22. **Portal del cliente** — login propio para ver sus cotizaciones / pedidos / envíos / entregas / facturas

---

## 11. 🔢 Estadísticas del proyecto

```
Modelos SQLAlchemy:        ~14
Routers FastAPI:           ~22
Schemas Pydantic:          ~10
Plantillas Jinja2:         ~25
Servicios:                 ~12
Endpoints HTTP:            ~120+
Líneas de código (app/):   ~9,500
```

---

## 12. 📦 Variables de entorno relevantes

```bash
# Auth
JWT_SECRET=…
JWT_ALGORITHM=HS256
JWT_EXP_DAYS=7

# DB
DB_HOST=98.89.231.141
DB_NAME=hecorp_clean
DB_USER=admin
DB_PASS=…

# Twilio
TWILIO_ACCOUNT_SID=…
TWILIO_AUTH_TOKEN=…
TWILIO_FROM=+1…           # ⚠️ pendiente número MX
TWILIO_TO_ADMIN=+522712120182

# Resend (correo)
RESEND_API_KEY=…           # ⚠️ pendiente
RESEND_FROM=cotizaciones@hecorp.com.mx

# Telegram
TELEGRAM_BOT_TOKEN=…
TELEGRAM_CHAT_ID=…
```

---

> _Última actualización: 2026-04-24 · `f6c833d`_
> _Hecho con caña, café y muy poco sueño 🖤_
