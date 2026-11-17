# Desarrollo local y publicación de Django

## Desarrollo con Angular

Ejecuta Django en el puerto 8000 y Angular en el 4200:

```powershell
python manage.py runserver 127.0.0.1:8000
ng serve
```

`CORS_ALLOWED_ORIGINS` ya permite `http://localhost:4200` y `http://127.0.0.1:4200`.

## Docker

```powershell
docker compose up --build
```

El contenedor aplica migraciones, importa el dataset si todavía no existe y ejecuta la aplicación ASGI con Uvicorn.

## Producción

Variables mínimas:

```text
DJANGO_SECRET_KEY=una-clave-segura-y-larga
DJANGO_DEBUG=false
ALLOWED_HOSTS=api.tudominio.com
DATABASE_URL=postgresql+psycopg://usuario:contraseña@host:5432/mb230
CORS_ALLOWED_ORIGINS=["https://tu-frontend.example"]
```

Secuencia de despliegue:

```powershell
python manage.py migrate
python manage.py import_dataset
python manage.py collectstatic --noinput
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

Recomendaciones:

- Usa PostgreSQL y HTTPS en producción.
- Restringe `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` a los dominios reales.
- Ejecuta `/health/ready`; debe devolver `question_count: 463`.
- Guarda la base de datos y los medios en almacenamiento persistente.
- No es necesario incluir el PDF original en el servidor: basta el dataset canónico y `data/media`.

## Render + Neon

El repositorio incluye `render.yaml` y `build.sh`. En Render, crea un Blueprint desde la rama
`backend` y proporciona `DATABASE_URL` con la cadena de conexión PostgreSQL agrupada (pooled) de
Neon. El servicio ejecuta migraciones e importa el dataset y sus traducciones antes de arrancar.

Cuando Render entregue la URL pública, comprueba:

```text
https://TU-SERVICIO.onrender.com/health/ready
https://TU-SERVICIO.onrender.com/docs/
```
