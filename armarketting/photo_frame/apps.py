from django.apps import AppConfig


class PhotoFrameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'photo_frame'

    def ready(self):
        import photo_frame.signals
