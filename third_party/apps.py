from django.apps import AppConfig


class ThirdPartyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'third_party'
    verbose_name = 'Third Party Management'
