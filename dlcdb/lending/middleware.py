def htmx_middleware(get_response):

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        # print(f"{request.META=}")
        request.htmx = True if request.META.get("HTTP_HX_REQUEST") else False
        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware
