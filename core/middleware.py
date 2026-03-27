from django.http import HttpResponse


class AzureHealthProbeMiddleware:
    """
    Intercept Azure App Service internal health probe requests (169.254.x.x)
    before SecurityMiddleware raises DisallowedHost.
    Must be first in MIDDLEWARE.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.META.get('HTTP_HOST', '')
        if host.startswith('169.254.'):
            return HttpResponse('OK')
        return self.get_response(request)
