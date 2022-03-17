from .models import LendingConfiguration

def lending_configuration(request):
    return {'lending_configuration': LendingConfiguration.load()}
