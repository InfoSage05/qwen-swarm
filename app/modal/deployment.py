import modal
from app.config import settings

app = modal.App(settings.MODAL_APP_NAME)
MODEL_VOLUME = modal.Volume.from_name(f"{settings.MODAL_APP_NAME}-weights", create_if_missing=True)
MODEL_DIR = "/model-weights"
