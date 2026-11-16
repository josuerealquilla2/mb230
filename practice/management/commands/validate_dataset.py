from django.core.management.base import BaseCommand, CommandError

from practice.dataset import DatasetValidationError, validate_dataset


class Command(BaseCommand):
    help = "Valida orden, hashes y recursos del dataset canónico"

    def handle(self, *args, **options) -> None:  # type: ignore[no-untyped-def]
        try:
            manifest, questions = validate_dataset()
        except DatasetValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Dataset válido: {len(questions)} preguntas; SHA-256 {manifest['dataset_sha256']}"
            )
        )
