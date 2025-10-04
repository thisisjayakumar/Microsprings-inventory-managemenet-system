from django.core.management.base import BaseCommand
from microsprings_inventory_system.sync_system.sync_service import sync_service
import time

class Command(BaseCommand):
    help = 'Start database synchronization service'
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting database sync service...')
        )
        sync_service.start_sync_service()
        
        try:
            # Keep the service running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sync_service.stop_sync_service()
            self.stdout.write(
                self.style.SUCCESS('Sync service stopped gracefully')
            )