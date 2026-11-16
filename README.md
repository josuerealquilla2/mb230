# MB-230 Practice API — Django

Backend Django REST Framework para practicar las 463 preguntas de `mb-230_Completo.pdf` en el mismo orden del documento. Está preparado para conectarse a un frontend Angular mediante JSON y CORS.

## Tecnologías

- Django 5.2 y Django REST Framework.
- OpenAPI/Swagger mediante drf-spectacular.
- CORS autorizado para Angular en `http://localhost:4200`.
- SQLite para desarrollo y PostgreSQL mediante `DATABASE_URL` para producción.
- Administración Django en `/admin/`.
- Imágenes y recortes del PDF servidos desde `/media/`.
- Registro e inicio de sesión con usuario y contraseña mediante tokens.
- Progreso, sesiones y configuración guardados por usuario.
- Traducción española estática para las 463 preguntas, sus 1.033 opciones y 768 comentarios.

## Iniciar el backend

Desde esta carpeta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py validate_dataset
python manage.py import_dataset
python manage.py runserver 127.0.0.1:8000
```

Abre:

- Swagger: `http://127.0.0.1:8000/docs/`
- Esquema OpenAPI: `http://127.0.0.1:8000/api/schema/`
- Administración: `http://127.0.0.1:8000/admin/`
- Estado: `http://127.0.0.1:8000/health/ready`

Para crear un administrador:

```powershell
python manage.py createsuperuser
```

## Conexión desde Angular

Configura en Angular:

```typescript
export const environment = {
  apiUrl: 'http://127.0.0.1:8000/api/v1'
};
```

Ejemplo de servicio:

```typescript
getQuestions(afterOrder = 0, limit = 20, questionType?: string) {
  let params: Record<string, string> = {
    after_order: String(afterOrder),
    limit: String(limit)
  };
  if (questionType) params['question_type'] = questionType;

  return this.http.get(`${environment.apiUrl}/exams/mb-230/questions`, { params });
}
```

## Filtros de preguntas

`GET /api/v1/exams/mb-230/questions`

| Parámetro | Uso |
|---|---|
| `after_order` | Devuelve preguntas posteriores a esa posición |
| `limit` | Cantidad de resultados, entre 1 y 100 |
| `question_type` | `single_choice`, `multiple_choice`, `yes_no`, `drag_drop` o `hotspot` |

Ejemplo:

```text
GET /api/v1/exams/mb-230/questions?after_order=20&limit=10&question_type=single_choice
```

## Flujo de práctica

Primero crea una cuenta o inicia sesión:

```json
POST /api/v1/auth/register
{
  "username": "mi_usuario",
  "password": "mi-clave-segura"
}
```

Las rutas de práctica requieren la cabecera `Authorization: Token <token>`. `GET /api/v1/practice-sessions` devuelve las sesiones del usuario para continuar otro día.

Crear una sesión:

```json
POST /api/v1/practice-sessions
{
  "exam_slug": "mb-230",
  "mode": "sequential",
  "from_order": 1,
  "to_order": 463
}
```

Después:

1. `GET /api/v1/practice-sessions/{id}/next` devuelve la pregunta actual sin solución.
2. `POST /api/v1/practice-sessions/{id}/answers` recibe la respuesta.
3. La respuesta del POST revela solución, explicación, comentarios y material visual.
4. Una nueva petición a `/next` devuelve la siguiente pregunta del PDF.

## Comandos de calidad

```powershell
python manage.py check
python manage.py validate_dataset
pytest
ruff check .
python manage.py spectacular --validate --file schema.yml
```

El dataset canónico está en `data/canonical/questions.jsonl`. Cada pregunta y recurso visual tiene hashes SHA-256 para detectar modificaciones. `source_answer` conserva la respuesta publicada en la fuente; `verified_answer` queda separado para una futura revisión independiente.

Las traducciones se guardan aparte en `data/translations/es.jsonl`. La importación valida que exista una traducción para cada pregunta, opción y comentario antes de escribirla en la base de datos. El texto inglés canónico nunca se reemplaza. Para volver a aplicar el corpus ejecuta `python manage.py import_translations`.

Consulta [docs/data-contract.md](docs/data-contract.md) y [docs/deployment.md](docs/deployment.md).
