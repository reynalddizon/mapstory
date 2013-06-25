from django.core.management.base import BaseCommand
from mapstory.social_signals import batch_notification

class Command(BaseCommand):

    def handle(self, *args, **opts):
        batch_notification()
