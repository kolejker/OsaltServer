import threading
import signal
import sys
from http.server import HTTPServer
from database import DatabaseManager
from handlers import TokenManager
from http_server import OsuHTTPRequestHandler

class OsuServer:
    
    def __init__(self, host='127.0.0.1', port=13381):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
        self.db_manager = DatabaseManager()
        self.token_manager = TokenManager()
        
        print(f"Starting server: {host}:{port}")
        self._print_user_stats()
    
    def _print_user_stats(self):
        users = self.db_manager.get_all_users()
        if users:
            print(f"\nUsers ({len(users)}):")
            for user in users[:5]:
                print(f"  • {user.username} (ID: {user.id})")
            if len(users) > 5:
                print(f"  ... and {len(users) - 5} more")
        else:
            print("no users registered")
        print()
    
    def start(self):
        handler = lambda *args, **kwargs: OsuHTTPRequestHandler(
            *args, server_instance=self, **kwargs
        )
        
        self.server = HTTPServer((self.host, self.port), handler)
        self.running = True
        
        print(f"server on: http://{self.host}:{self.port}/")
        print("fish eater")
        print("=" * 40)
        
        def serve_forever():
            try:
                self.server.serve_forever()
            except Exception as e:
                if self.running:
                    print(f"error: {e}")
        
        self.server_thread = threading.Thread(target=serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def stop(self):
        self.running = False
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.server_thread:
            self.server_thread.join(timeout=1)
        print("stopped")


def main():
    server = OsuServer()
    
    def signal_handler(sig, frame):
        print("\nstopping")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        server.start()
        while server.running:
            import time
            time.sleep(0.1)
    except Exception as e:
        print(f"error: {e}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()