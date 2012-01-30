# -*- coding: utf-8 -*-
"""
    sockjs.tornado.transports.websocket
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Websocket transport implementation
"""
import logging
import socket

from sockjs.tornado import proto, websocket, session


class RawSession(session.BaseSession):
    def send_message(self, msg):
        # TODO: Optimize - get rid of double JSON encoding?
        decoded = proto.json_decode(msg)

        if not isinstance(decoded, basestring):
            raise Exception('Can only send strings over raw websocket transport')

        self.handler.send_pack(decoded)

    def on_message(self, msg):
        self.conn.on_message(msg.decode('utf-8'))


class RawWebSocketTransport(websocket.WebSocketHandler):
    """Raw Websocket transport"""
    name = 'rawwebsocket'

    def initialize(self, server):
        self.server = server
        self.session = None

    def open(self):
        # Stats
        self.server.stats.on_conn_opened()

        # Disable nagle
        #if self.server.settings['disable_nagle']:
        self.stream.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

        # Handle session
        self.session = RawSession(self.server.get_connection_class(), self.server)

        self.session.set_handler(self)
        self.session.verify_state()

    def _detach(self):
        if self.session is not None:
            self.session.remove_handler(self)
            self.session = None

    def on_message(self, message):
        # Ignore empty messages
        if not message or not self.session:
            return

        try:
            self.session.on_message(message)
        except Exception:
            logging.exception('RawWebSocket')

            # Close running connection
            self._detach()
            self.abort_connection()

    def on_close(self):
        # Close session if websocket connection was closed
        if self.session is not None:
            # Stats
            self.server.stats.on_conn_closed()

            session = self.session
            self._detach()
            session.close()

    def send_pack(self, message):
        # Send message
        try:
            self.write_message(message)
        except IOError:
            self.server.io_loop.add_callback(self.on_close)

    def session_closed(self):
        try:
            self.close()
        except IOError:
            pass
        finally:
            self._detach()

    # Websocket overrides
    def allow_draft76(self):
        return True
