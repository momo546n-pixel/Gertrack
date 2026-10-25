import threading

_thread_locals = threading.local()


def get_current_request():
    """Retourne la requête HTTP en cours de traitement dans ce thread, si disponible."""
    return getattr(_thread_locals, 'request', None)


def get_client_ip(request):
    """Extrait l'adresse IP du client, en tenant compte d'un éventuel proxy."""
    if request is None:
        return None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class CurrentRequestMiddleware:
    """
    Conserve la requête courante dans un thread-local afin que AuditLog.log()
    puisse retrouver l'adresse IP de l'utilisateur sans avoir besoin qu'on la
    lui passe explicitement à chacun de ses (nombreux) points d'appel.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            _thread_locals.request = None
