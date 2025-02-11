from django.apps import AppConfig


<<<<<<<< HEAD:components/apps.py
class ComponentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'components'
========
class DynamicTablesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dynamic_tables'
>>>>>>>> 1afc9bba66615380003bbbac2b1f2f322bc00c44:dynamic_tables/apps.py
