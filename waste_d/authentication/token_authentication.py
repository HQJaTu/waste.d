from rest_framework.authentication import TokenAuthentication
from waste_d.models.sql.token_auth import WastedToken


class WastedTokenAuthentication(TokenAuthentication):
    model = WastedToken

    # Meta options: https://docs.djangoproject.com/en/3.1/ref/models/options/
    class Meta:
        db_table = 'authtoken_token'
