from django.conf import settings


def firebase_config(request):
    """Expose only runtime Firebase web configuration to the templates that need it."""
    return {"firebase_config": settings.FIREBASE_CONFIG}
