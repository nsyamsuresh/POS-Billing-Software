from django.urls import set_script_prefix


class MobilePrefixMiddleware:
    """Serve the whole site under /m/ with the mobile layout.

    /m/products/ is handled as /products/, and every link on the page
    keeps the /m/ prefix, so the user stays in the mobile layout.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_mobile = False
        path = request.path_info
        if path == '/m' or path.startswith('/m/'):
            request.is_mobile = True
            request.path_info = path[2:] or '/'
            set_script_prefix('/m/')
        return self.get_response(request)