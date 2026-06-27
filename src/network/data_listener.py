from PyQt6.QtCore import QObject, pyqtSignal, QByteArray, QJsonDocument
from PyQt6.QtNetwork import QTcpServer, QHostAddress, QTcpSocket
import logging

class DataListener(QObject):
    """
    Listens for TCP connections from the external helper (C#).
    Expects newline-delimited JSON.
    """
    data_received = pyqtSignal(dict)
    
    def __init__(self, port=65432, parent=None):
        super().__init__(parent)
        self.port = port
        self.server = QTcpServer(self)
        self.logger = logging.getLogger(__name__)
        
        # Connection handling
        self.server.newConnection.connect(self._handle_new_connection)
        
        self.clients = []
        
        # self._start_server() # Don't auto-start

    def start_listening(self):
        if not self.server.isListening():
            if self.server.listen(QHostAddress.SpecialAddress.LocalHost, self.port):
                self.logger.info(f"DataListener listening on port {self.port}")
                return True
            else:
                self.logger.error(f"Failed to start DataListener: {self.server.errorString()}")
                return False
        return True

    def stop_listening(self):
        if self.server.isListening():
            self.server.close()
            self.logger.info("DataListener stopped listening")
        
        # Disconnect clients
        for socket in self.clients:
            socket.disconnectFromHost()
        self.clients.clear()

    def _handle_new_connection(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self._read_data(s))
            socket.disconnected.connect(lambda s=socket: self._client_disconnected(s))
            self.clients.append(socket)
            self.logger.info("New client connected")

    def _read_data(self, socket):
        # Read all available data
        data = socket.readAll()
        # Handle potential fragmentation or multiple messages?
        # For simplicity, assume one JSON object per line/message for now.
        # Ideally we buffer split by newline.
        
        text = str(data, encoding='utf-8').strip()
        if not text:
            return
            
        try:
            # Parse JSON
            doc = QJsonDocument.fromJson(data)
            if not doc.isNull() and doc.isObject():
                json_obj = doc.object()
                # Convert to python dict
                py_dict = json_obj.toVariant()
                self.data_received.emit(py_dict)
            else:
                self.logger.warning(f"Received invalid JSON: {text}")
        except Exception:
            self.logger.exception("Error parsing tracker network data")

    def _client_disconnected(self, socket):
        self.logger.info("Client disconnected")
        if socket in self.clients:
            self.clients.remove(socket)
        socket.deleteLater()
