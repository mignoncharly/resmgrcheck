from django.conf import settings
from django.utils import timezone

def product(request):return {'environment':settings.ENVIRONMENT,'now':timezone.now(),'product_version':'ResMgrCheck Web','is_account_page':request.path.startswith('/accounts/')}
