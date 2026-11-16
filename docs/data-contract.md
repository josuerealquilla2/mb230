# Contrato de datos

## Fuente canónica

La aplicación importa `data/canonical/questions.jsonl`. Es JSON Lines: una pregunta completa por línea, ordenada por `pdf_order`. `manifest.json` fija la cantidad, los hashes del PDF y del dataset, y los conteos por tipo. `qa-report.json` registra cualquier incidencia detectada durante la conversión.

Campos relevantes de una pregunta:

| Campo | Significado |
|---|---|
| `id` | Identificador estable, por ejemplo `mb230-q0001` |
| `pdf_order` | Posición estricta dentro del PDF |
| `raw_text` | Texto completo extraído para auditoría |
| `prompt_text` | Enunciado listo para presentar |
| `options` | Opciones en su orden original |
| `source_answer` | Respuesta indicada por la fuente, sin reinterpretarla |
| `verified_answer` | Campo separado para revisión humana futura |
| `explanation_raw` | Explicación completa de la fuente |
| `community_discussion_raw` | Discusión completa sin estructurar |
| `community_comments` | Comentarios estructurados de forma adicional |
| `interaction` | Forma de respuesta y modo de corrección |
| `media` | Imágenes con función, origen, dimensiones y SHA-256 |
| `source_fragments` | Páginas, cajas y texto que forman la pregunta |
| `content_sha256` | Huella del registro completo |

## Separación entre contenido público y solución

`QuestionPublic` contiene únicamente los datos necesarios para responder. No expone `source_answer`, `verified_answer`, `explanation_raw`, discusión ni material visual marcado como respuesta. Esos campos aparecen en `AnswerFeedback` después de enviar una respuesta.

## Recursos visuales

Los archivos están en `data/media/{dos_primeros_caracteres}/{sha256}.webp`. WebP se usa en modo sin pérdida. Las funciones posibles son:

- `question_asset`: recurso necesario para contestar; es público.
- `answer_asset`: solución o material posterior; solo se revela al responder.
- `comment_asset`: recurso perteneciente a la discusión.
- `source_fragment`: recorte exacto del intervalo original; se conserva para auditoría y se revela tras responder.

## Compatibilidad futura

`schema_version` permite migrar el dataset sin modificar silenciosamente registros anteriores. Una corrección editorial debe crear una nueva versión del dataset y conservar el hash de la fuente original.

