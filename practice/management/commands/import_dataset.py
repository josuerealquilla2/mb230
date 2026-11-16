from django.core.management.base import BaseCommand, CommandError

from practice.dataset import DatasetValidationError, import_canonical_dataset


class Command(BaseCommand):
    help = "Valida e importa el dataset canónico MB-230"

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        try:
            exam = import_canonical_dataset(replace=options["replace"])
        except DatasetValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(f"Importadas {exam.question_count} preguntas para {exam.slug}.")
        )
