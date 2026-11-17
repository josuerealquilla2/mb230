# MB-230 Practice Frontend

Frontend Angular independiente para la API Django MB-230. Está preparado para vivir en un repositorio de GitHub distinto al backend.

## Desarrollo local

El backend debe estar disponible en `http://127.0.0.1:8000`.

```powershell
npm install
npm start
```

Abre `http://localhost:4200`.

## Configuración de la API

Desarrollo: `src/environments/environment.development.ts`.

Producción: `src/environments/environment.ts`.

Antes de publicar frontend y backend en servicios diferentes, cambia `apiUrl` en el archivo de producción:

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://api.tudominio.com/api/v1'
};
```

En Django añade el dominio del frontend a `CORS_ALLOWED_ORIGINS`.

## Publicar gratis en Vercel

El frontend y el backend se despliegan por separado. Vercel alojará este proyecto Angular; Django debe estar publicado en otro servicio con una URL HTTPS pública.

1. Sube esta carpeta a un repositorio de GitHub independiente.
2. En Vercel, selecciona **Add New → Project** e importa ese repositorio.
3. Vercel leerá automáticamente `vercel.json`; no es necesario cambiar el comando ni la carpeta de salida.
4. En **Settings → Environment Variables**, crea:

   - Nombre: `API_URL`
   - Valor: `https://tu-backend.example.com/api/v1`
   - Entornos: Production y Preview

5. Pulsa **Deploy**. Las rutas internas como `/questions` y `/practice/...` funcionarán al recargar gracias a la reescritura SPA incluida.

Después, configura el backend Django para permitir el dominio asignado por Vercel:

```python
CORS_ALLOWED_ORIGINS = [
    "https://tu-frontend.vercel.app",
]
CSRF_TRUSTED_ORIGINS = [
    "https://tu-frontend.vercel.app",
]
```

Cada cambio enviado a la rama principal generará un despliegue nuevo. Las pull requests también pueden generar vistas previas gratuitas.

## Publicar el frontend en Cloudflare Pages

Conecta el repositorio de GitHub y selecciona la rama `frontend`. Usa `npm run build:cloudflare` como comando de compilación y `dist/mb230-practice-frontend` como directorio de salida. Añade la variable `API_URL` con la URL HTTPS pública del backend Django, terminada en `/api/v1`.

Si la cuenta muestra únicamente el flujo nuevo de Cloudflare Workers, utiliza `npm run build:cloudflare` como Build command y `npx wrangler deploy` como Deploy command. El archivo `wrangler.jsonc` publica el contenido de `dist/mb230-practice-frontend` como recursos estáticos y configura la navegación SPA.

## Organización

```text
src/app/
├── core/
│   ├── interceptors/   # Manejo transversal de errores HTTP
│   ├── models/         # Contratos TypeScript de la API
│   └── services/       # Clientes HTTP y persistencia local
├── features/
│   ├── home/           # Inicio y creación de sesiones
│   ├── questions/      # Explorador y filtros
│   └── practice/       # Respuesta, corrección y progreso
└── shared/             # Componentes reutilizables
```

El proyecto usa componentes standalone, carga diferida por ruta, señales, formularios reactivos, tipado estricto, detección `OnPush`, Bootstrap 5 sin JavaScript adicional, interceptor de autenticación y diseño responsive accesible.

## Funcionalidad incluida

- Registro e inicio de sesión solicitando únicamente usuario y contraseña.
- Examen completo de 463 preguntas en el orden del PDF.
- Sesiones guardadas en Django para continuar otro día o desde otro dispositivo.
- Pregunta original y traducción española completa, sin alterar el contenido original.
- Respuestas, corrección, comentarios y recursos visuales.
- Panel de progreso ocultable y recuperable en ordenador, tablet y teléfono.
- Configuración del recorrido, traducciones y tamaño predeterminado.
- Temas claro, oscuro y automático según el dispositivo.
- Navegación adaptada a escritorio, tablet y teléfono.

## Comandos

```powershell
npm start
npm run build:production
npm run build:vercel
npm test
```

El resultado para hosting estático se genera dentro de `dist/mb230-practice-frontend`.
