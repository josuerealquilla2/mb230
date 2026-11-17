from dataclasses import dataclass

from django.db.models import Q


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    description: str
    terms: tuple[str, ...]


TOPICS = (
    Topic("routing", "Enrutamiento, reglas y colas", "Routing rules, workstreams y asignación a colas.", ("routing", "route to", "workstream", "queue")),
    Topic("cases", "Gestión de casos", "Creación, resolución y administración de casos.", ("case", "cases", "incident")),
    Topic("knowledge", "Administración del conocimiento", "Artículos, búsqueda y bases de conocimiento.", ("knowledge", "article", "knowledge base")),
    Topic("sla", "SLA y derechos", "Acuerdos de nivel de servicio, hitos y entitlement.", ("sla", "service level", "entitlement", "kpi")),
    Topic("omnichannel", "Omnicanal y conversaciones", "Canales, conversaciones, agentes y atención digital.", ("omnichannel", "conversation", "chat", "agent", "channel")),
    Topic("scheduling", "Programación y recursos", "Calendarios, reservas, recursos y Universal Resource Scheduling.", ("schedule", "scheduling", "booking", "resource", "calendar")),
    Topic("analytics", "Analítica e informes", "Paneles, métricas, insights e informes.", ("analytics", "report", "dashboard", "insight", "metric")),
    Topic("automation", "Automatización y procesos", "Flujos, Power Automate y procesos de negocio.", ("workflow", "power automate", "business process", "process flow", "automation")),
    Topic("email", "Correo y creación automática", "Correo, buzones y creación automática de registros.", ("email", "mailbox", "automatic record", "record creation")),
    Topic("surveys", "Customer Voice y satisfacción", "Encuestas, invitaciones y satisfacción del cliente.", ("customer voice", "survey", "satisfaction", "invitation")),
    Topic("security", "Seguridad y permisos", "Roles, privilegios, equipos y acceso.", ("security", "role", "privilege", "permission", "access team")),
    Topic("connected", "Connected Customer Service e IoT", "Dispositivos, alertas IoT y servicio conectado.", ("iot", "connected customer", "device", "iot alert")),
)


def get_topic(topic_id: str) -> Topic | None:
    return next((topic for topic in TOPICS if topic.id == topic_id), None)


def topic_query(topic: Topic) -> Q:
    query = Q()
    for term in topic.terms:
        query |= Q(prompt_text__icontains=term)
        query |= Q(raw_text__icontains=term)
        query |= Q(explanation_raw__icontains=term)
        query |= Q(community_discussion_raw__icontains=term)
    return query
