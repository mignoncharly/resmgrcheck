from django.apps import AppConfig
class ControlConfig(AppConfig):
    name='control'
    def ready(self):
        from . import signals
