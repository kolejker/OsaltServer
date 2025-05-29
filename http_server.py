from http.server import BaseHTTPRequestHandler
from handlers import LoginHandler, PacketHandler, TokenManager

class OsuHTTPRequestHandler(BaseHTTPRequestHandler):
    
    def __init__(self, *args, server_instance=None, **kwargs):
        self.server_instance = server_instance
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        pass
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            osu_token = self.headers.get('osu-token')
            
            if not osu_token:
                self._handle_login_request(body)
            else:
                self._handle_authenticated_request(osu_token, body)
                
        except Exception as e:
            print(f"request error {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
    
    def _handle_login_request(self, body: bytes):
        login_handler = LoginHandler(
            self.server_instance.db_manager,
            self.server_instance.token_manager
        )
        
        success, response_data, token = login_handler.handle_login(body)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        if token:
            self.send_header('cho-token', token)
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)
    
    def _handle_authenticated_request(self, osu_token: str, body: bytes):
        user_data = self.server_instance.token_manager.get_user(osu_token)
        
        if not user_data:
            print(f"invalid token: {osu_token}")
            self.send_response(401)
            self.end_headers()
            return
        
        print(f"packet from {user_data.username} (ID: {user_data.user_id})")
        
        packet_handler = PacketHandler(self.server_instance.token_manager)
        response_packets = packet_handler.process_packets(user_data, body)
    
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(response_packets)))
        self.end_headers()
        self.wfile.write(response_packets)