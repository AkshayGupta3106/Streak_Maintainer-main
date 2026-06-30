from django.apps import AppConfig
import os
import threading
import time
import logging

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Prevent running twice in reloader
        if os.environ.get('RUN_MAIN') == 'true':
            from django.core.management import call_command
            try:
                call_command('makemigrations', 'core', interactive=False)
                call_command('migrate', interactive=False)
                print("Django Migrations Executed Programmatically successfully.")
            except Exception as e:
                print("Django Programmatic Migration Run encountered an error:", e)
            threading.Thread(target=self.start_scheduler, daemon=True, name="StreakMaintainerScheduler").start()

    def start_scheduler(self):
        # Wait a short while to ensure the app is fully loaded and DB is ready
        time.sleep(5)
        
        from core.services.sync_engine import run_contest_sync, run_reminder_dispatch
        
        logger = logging.getLogger(__name__)
        logger.info("Background contest sync & reminder scheduler thread started.")
        
        last_sync_time = 0
        sync_interval = 1800 # 30 minutes
        
        while True:
            try:
                # 1. Run reminder dispatch (every 1 min)
                run_reminder_dispatch()
                
                # 2. Run contest sync (every 30 mins)
                now_epoch = time.time()
                if now_epoch - last_sync_time >= sync_interval:
                    run_contest_sync()
                    last_sync_time = now_epoch
                    
            except Exception as e:
                logger.error(f"Error in scheduler thread loop: {e}")
                
            time.sleep(60)
