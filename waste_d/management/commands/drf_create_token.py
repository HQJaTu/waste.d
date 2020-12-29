"""
Additional treatment for the loaddata command.
Location example: project/app/management/commands/loaddata.py
"""
from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.management.commands import drf_create_token
from waste_d.models.sql.token_auth import WastedToken


class Command(drf_create_token.Command):
    """
    Docs:
    https://docs.djangoproject.com/en/3.1/howto/custom-management-commands/

    Source code:
    https://github.com/encode/django-rest-framework/blob/master/rest_framework/authtoken/management/commands/drf_create_token.py

    Note:
        Make sure to have this app before rest_framework.authtoken in INSTALLED_APPS.
    """
    help = 'Create DRF Token for a given user, platform and channel'

    def create_wasted_user_token(self, username, reset_token, platform, chat):
        user = drf_create_token.UserModel._default_manager.get_by_natural_key(username)

        if reset_token:
            WastedToken.objects.filter(user=user).delete()

        token = WastedToken.objects.get_or_create(user=user, platform=platform, chat=chat)
        return token[0]

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument(
            '-r',
            '--reset',
            action='store_true',
            dest='reset_token',
            default=False,
            help='Reset existing User token and create a new one',
        )
        parser.add_argument('platform', type=str,
                            help='Hard-coded platform ID')
        parser.add_argument('chat', type=str,
                            nargs='?',
                            help='(optional) Hard-coded chat in platform. Irc has nets, Discord has servers,'
                                 'Slack has workspaces.')

    def handle(self, *args, **options):
        username = options['username']
        reset_token = options['reset_token']
        platform = options['platform']
        chat = options['chat']

        try:
            token = self.create_wasted_user_token(username, reset_token, platform, chat)
        except drf_create_token.UserModel.DoesNotExist:
            raise CommandError(
                'Cannot create the Token: user {} does not exist'.format(
                    username)
            )
        self.stdout.write(
            'Generated token {} for user {}'.format(token.key, username))