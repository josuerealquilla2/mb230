from django.core.management.base import BaseCommand, CommandError

from practice.dataset import DatasetValidationError, apply_translations
from practice.models import Exam


class Command(BaseCommand):
    help = "Valida e importa las traducciones españolas sin modificar el dataset canónico"

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        exam = Exam.objects.filter(slug="mb-230").first()
        if exam is None:
            raise CommandError("Primero debes importar el dataset canónico.")
        try:
            count = apply_translations(exam)
        except DatasetValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Importadas traducciones para {count} preguntas."))
