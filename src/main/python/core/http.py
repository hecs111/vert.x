# Copyright 2011-2012 the original author or authors.   
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" 
This module adds the http support to the python vert.x platform 
"""

import org.vertx.java.deploy.impl.VertxLocator
import core.tcp_support
import core.ssl_support
import core.buffer
import core.streams

from core.javautils import map_from_java, map_to_java
from core.handlers import CloseHandler, ClosedHandler, ExceptionHandler
from core.handlers import DoneHandler, ContinueHandler, BufferHandler


__author__ = "Scott Horn"
__email__ = "scott@hornmicro.com"

class HttpServer(core.tcp_support.TCPSupport, core.ssl_support.SSLSupport, object):
    """ An HTTP and websockets server """
    def __init__(self, **kwargs):
        self.java_obj = org.vertx.java.deploy.impl.VertxLocator.vertx.createHttpServer()
        for item in kwargs.keys():
           setattr(self, item, kwargs[item])

    def request_handler(self, handler):
        """Set the HTTP request handler for the server.
        As HTTP requests arrive on the server a new HttpServerRequest instance will be created and passed to the handler.

        Keyword arguments:
        handler -- the function used to handle the request. 

        """
        self.java_obj.requestHandler(HttpServerRequestHandler(handler))

    def websocket_handler(self, handler):
        """Set the websocket handler for the server.
        As websocket requests arrive on the server a new ServerWebSocket instance will be created and passed to the handler.

        Keyword arguments:
        handler -- the function used to handle the request. 

        """
        self.java_obj.websocketHandler(ServerWebSocketHandler(handler))

    def listen(self, port, host=None):
        """Instruct the server to listen for incoming connections. If host is None listens on all.

        Keyword arguments:
        port -- The port to listen on.
        host -- The host name or ip address to listen on. (default None)
    
        """
        if host is None:
            self.java_obj.listen(port)
        else:
            self.java_obj.listen(port, host)

    def client_auth_required(self, val):
        """ Client authentication is an extra level of security in SSL, and requires clients to provide client certificates.
        Those certificates must be added to the server trust store.

        Keyword arguments:
        val -- If true then the server will request client authentication from any connecting clients, if they 
        do not authenticate then they will not make a connection.

        """
        self.java_obj.setClientAuthRequired(val)
        return self

    def close(self, handler=None):
        """ Close the server. Any open HTTP connections will be closed. This can be used as a decorator.

        Keyword arguments:
        handler -- a handler that is called when the connection is closed. The handler is wrapped in a ClosedHandler.

        """
        if handler is None:
            self.java_obj.close()
        else:
            self.java_obj.close(CloseHandler(handler))

    def _to_java_server():
        """ private """
        return self.java_obj

class HttpClient(core.ssl_support.SSLSupport, core.tcp_support.TCPSupport, object):
    """ An HTTP client.
     A client maintains a pool of connections to a specific host, at a specific port. The HTTP connections can act
     as pipelines for HTTP requests.
     It is used as a factory for HttpClientRequest instances which encapsulate the actual HTTP requests. It is also
     used as a factory for HTML5 WebSocket websockets.
    """
    def __init__(self, **kwargs):
        self.java_obj = org.vertx.java.deploy.impl.VertxLocator.vertx.createHttpClient()
        for item in kwargs.keys():
           setattr(self, item, kwargs[item])

    def exception_handler(self, handler):
        """ Set the exception handler.

        Keyword arguments
        handler -- function to be used as the handler
        """
        self.java_obj.exceptionHandler(ExceptionHandler(handler))
        return self
    
    def get_max_pool_size(self):
        """The maxium number of connections this client will pool."""
        return self.java_obj.getMaxPoolSize

    def set_max_pool_size(self, val):
        """ Set the maximum pool size.
        The client will maintain up to this number of HTTP connections in an internal pool

        Keyword arguments
        val -- The maximum number of connections (default to 1).
        """
        self.java_obj.setMaxPoolSize(val)
        return self

    max_pool_size = property(get_max_pool_size, set_max_pool_size)

    def set_keep_alive(self, val):
        """If val is true then, after the request has ended the connection will be returned to the pool
        where it can be used by another request. In this manner, many HTTP requests can be pipe-lined over an HTTP connection.
        Keep alive connections will not be closed until the close method is invoked.
        If val is false then a new connection will be created for each request and it won't ever go in the pool,
        the connection will closed after the response has been received. Even with no keep alive, the client will not allow more
        than max_pool_size connections to be created at any one time.

        Keyword arguments
        val -- The value to use for keep_alive
        """
        self.java_obj.setTCPKeepAlive(val)
        return self

    keep_alive = property(fset=set_keep_alive)

    def set_trust_all(self, val):
        """Should the client trust ALL server certificates?

        Keyword arguments
        val -- If val is set to true then the client will trust ALL server certificates and will not attempt to authenticate them
        against it's local client trust store. The default value is false.
        Use this method with caution!
        """
        self.java_obj.setTrustAll(val)
        return self

    trust_all = property(fset=set_trust_all)

    def set_port(self, val):
        """Set the port that the client will attempt to connect to on the server on. The default value is 80

        Keyword arguments
        val -- The port value.
        """
        self.java_obj.setPort(val)
        return self

    port = property(fset=set_port)

    def set_host(self, val):
        """Set the host name or ip address that the client will attempt to connect to on the server on.

        Keyword arguments
        val -- The host name or ip address to connect to.
        """
        self.java_obj.setHost(val)
        return self
    
    host = property(fset=set_host)

    def connect_web_socket(self, uri, handler):
        """Attempt to connect an HTML5 websocket to the specified URI.
        The connect is done asynchronously and the handler is called with a WebSocket on success.

        Keyword arguments
        uri -- A relative URI where to connect the websocket on the host, e.g. /some/path
        handler -- The handler to be called with the WebSocket
        """
        self.java_obj.connectWebsocket(uri, WebSocketHandler(handler))

    def get_now(self, uri, handler, **headers):
        """This is a quick version of the get method where you do not want to do anything with the request
        before sing.
        With this method the request is immediately sent.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
         uri -- A relative URI where to perform the GET on the server.
         handler -- The handler to be called with the HttpClientResponse
         headers -- A dictionary of headers to pass with the request.
        """
        if len(headers) == 0:
            self.java_obj.getNow(uri, HttpClientResponseHandler(handler))    
        else:
            self.java_obj.getNow(uri, map_to_java(headers), HttpClientResponseHandler(handler))    
        
    def options(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP OPTIONS request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the OPTIONS on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.options(uri, HttpClientResponseHandler(handler)))

    def get(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP GET request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the GET on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.get(uri, HttpClientResponseHandler(handler)))

    def head(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP HEAD request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the HEAD on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.head(uri, HttpClientResponseHandler(handler)))

    def post(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP POST request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the POST on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.post(uri, HttpClientResponseHandler(handler)))

    def put(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP PUT request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.
        
        Keyword arguments
        uri -- A relative URI where to perform the PUT on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.put(uri, HttpClientResponseHandler(handler)))

    def delete(self, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP DELETE request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the DELETE on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest.new(self.java_obj.delete(uri, HttpClientResponseHandler(handler)))

    def trace(self, uri, handler):
        """ This method returns an HttpClientRequest instance which represents an HTTP TRACE request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the TRACE on the server.
        handler. The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.trace(uri, HttpClientResponseHandler(handler)))

    def connect(self, uri, handler):
        """ This method returns an HttpClientRequest instance which represents an HTTP CONNECT request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.
        
        Keyword arguments
        uri -- A relative URI where to perform the CONNECT on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.connect(uri, HttpClientResponseHandler(handler)))

    def patch(self, uri, handler):
        """ This method returns an HttpClientRequest instance which represents an HTTP PATCH request with the specified uri.
        When an HTTP response is received from the server the handler is called passing in the response.

        Keyword arguments
        uri -- A relative URI where to perform the PATCH on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.patch(uri, HttpClientResponseHandler(handler)))

    def request(self, method, uri, handler):
        """This method returns an HttpClientRequest instance which represents an HTTP request with the specified method and uri.
        When an HTTP response is received from the server the handler is called passing in the response.
        method. The HTTP method. Can be one of OPTIONS, HEAD, GET, POST, PUT, DELETE, TRACE, CONNECT.

        Keyword arguments
        uri -- A relative URI where to perform the OPTIONS on the server.
        handler -- The handler to be called with the HttpClientResponse
        """
        return HttpClientRequest(self.java_obj.request(method, uri, HttpClientResponseHandler(handler)))

    def close():
        """Close the client. Any unclosed connections will be closed."""
        self.java_obj.close()

class HttpClientRequest(core.streams.WriteStream, object):
    """Instances of this class are created by an HttpClient instance, via one of the methods corresponding to the
     specific HTTP methods, or the generic HttpClient request method.

     Once an instance of this class has been obtained, headers can be set on it, and data can be written to its body,
     if required. Once you are ready to send the request, the end method must called.

     Nothing is sent until the request has been internally assigned an HTTP connection. The HttpClient instance
     will return an instance of this class immediately, even if there are no HTTP connections available in the pool. Any requests
     sent before a connection is assigned will be queued internally and actually sent when an HTTP connection becomes
     available from the pool.

     The headers of the request are actually sent either when the end method is called, or, when the first
     part of the body is written, whichever occurs first.

     This class supports both chunked and non-chunked HTTP.
    """
    def __init__(self, java_obj):
        self.java_obj = java_obj
        self.headers_dict = None

    @property
    def headers(self):
        """ Hash of headers for the request"""
        if self.headers_dict is None:
            self.headers_dict = map_from_java(self.java_obj.headers())
        return self.headers_dict
     
    def put_header(self, key, value):
        """Inserts a header into the request.

        Keyword arguments
        key -- The header key
        value -- The header value. to_s will be called on the value to determine the actual String value to insert.
        returns  self So multiple operations can be chained.
        """
        self.java_obj.putHeader(key, value)
        return self
     
    def write_buffer(self, chunk, handler):
        """Write a to the request body.

        Keyword arguments
        chunk -- The buffer to write.
        handler -- The handler will be called when the buffer has actually been written to the wire.
        returns  self So multiple operations can be chained.
        """
        self.java_obj.writeBuffer(chunk._to_java_buffer)
        return self

    def write_str(self, str, enc="UTF-8", handler=None):
        """Write a to the request body.

        Keyword arguments
        str -- The string to write.
        enc -- The encoding to use.
        handler -- The handler will be called when the buffer has actually been written to the wire.

        returns self So multiple operations can be chained.
        """
        if handler is None:
            self.java_obj.write(str, enc)
        else:
            self.java_obj.write(str, enc, DoneHandler(handler))
        return self

    def send_head(self):
        """Forces the head of the request to be written before end is called on the request. This is normally used
        to implement HTTP 100-continue handling, see continue_handler for more information.

        returns self So multiple operations can be chained.
        """
        self.java_obj.sendHead()
        return self

    def end(self):
        """Ends the request. If no data has been written to the request body, and send_head has not been called then
        the actual request won't get written until this method gets called.
        Once the request has ended, it cannot be used any more, and if keep alive is true the underlying connection will
        be returned to the HttpClient pool so it can be assigned to another request.
        """
        self.java_obj.end()

    def write_str_and_end(self, str, enc="UTF-8"):
        """Same as write_buffer_and_end but writes a String

        Keyword arguments
        str -- The String to write
        enc -- The encoding
        """
        self.java_obj.end(str, enc)

    def write_buffer_and_end(self, chunk):
        """Same as end but writes some data to the response body before ending. If the response is not chunked and
        no other data has been written then the Content-Length header will be automatically set

        Keyword arguments
        chunk -- The Buffer to write
        """
        self.java_obj.end(chunk._to_java_buffer)

    def set_chunked(self, val):
        """Sets whether the request should used HTTP chunked encoding or not.

        Keyword arguments
        val -- If val is true, this request will use HTTP chunked encoding, and each call to write to the body
        will correspond to a new HTTP chunk sent on the wire. If chunked encoding is used the HTTP header
        'Transfer-Encoding' with a value of 'Chunked' will be automatically inserted in the request.

        If chunked is false, this request will not use HTTP chunked encoding, and therefore if any data is written the
        body of the request, the total size of that data must be set in the 'Content-Length' header before any
        data is written to the request body.

        returns self So multiple operations can be chained.
        """
        self.java_obj.setChunked(val)
        return self

    chucked = property(fset=set_chunked)

    def continue_handler(self, handler):
        """If you send an HTTP request with the header 'Expect' set to the value '100-continue'
        and the server responds with an interim HTTP response with a status code of '100' and a continue handler
        has been set using this method, then the handler will be called.
        You can then continue to write data to the request body and later end it. This is normally used in conjunction with
        the send_head method to force the request header to be written before the request has ended.

        Keyword arguments
        handler -- The handler
        """
        self.java_obj.continueHandler(ContinueHandler(handler))

   
class HttpClientResponse(core.streams.ReadStream):
    """Encapsulates a client-side HTTP response.

    An instance of this class is provided to the user via a handler that was specified when one of the
    HTTP method operations, or the generic HttpClientrequest method was called on an instance of HttpClient.
    """
    def __init__(self, java_obj):
        self.java_obj = java_obj
        self.headers_dict = None
        self.trailers_dict = None
   
    @property
    def status_code(self):
        """return the HTTP status code of the response."""
        return self.java_obj.statusCode
  
    def header(self, key):
        """Get a header value

        Keyword arguments
        key -- The key of the header.

        return the header value.
        """
        return self.java_obj.getHeader(key)
  
    @property
    def headers(self):
        """Get all the headers in the response.
        If the response contains multiple headers with the same key, the values
        will be concatenated together into a single header with the same key value, with each value separated by a comma,
        as specified by {http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.htmlsec4.2}.
        return a dictionary of headers.
        """
        if self.headers_dict is None:
            self.headers_dict = map_from_java(self.java_obj.headers())
        return self.headers_dict
    
    @property
    def trailers(self):
        """Get all the trailers in the response.
        If the response contains multiple trailers with the same key, the values
        will be concatenated together into a single header with the same key value, with each value separated by a comma,
        as specified by {http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.htmlsec4.2}.
        Trailers will only be available in the response if the server has sent a HTTP chunked response where headers have
        been inserted by the server on the last chunk. In such a case they won't be available on the client until the last chunk has
        been received.
        
        return a dictionary of trailers."""
        if self.trailers_dict is None:
          self.trailers_dict = map_from_java(self.java_obj.trailers())
        return self.trailers_dict

    def body_handler(self, handler):
        """Set a handler to receive the entire body in one go - do not use this for large bodies"""
        self.java_obj.bodyHandler(BufferHandler(handler))
  
class HttpServerRequest(object):
    """ Encapsulates a server-side HTTP request.
  
    An instance of this class is created for each request that is handled by the server and is passed to the user via the
    handler specified using HttpServer.request_handler.

    Each instance of this class is associated with a corresponding HttpServerResponse instance via the property response.
    """
    def __init__(self, http_server_request):
        self.http_server_request = http_server_request
        self.http_server_response = HttpServerResponse(http_server_request.response)
        self.headers_dict = None
        self.params_dict = None
    
    @property
    def method(self):
        """ The HTTP method, one of HEAD, OPTIONS, GET, POST, PUT, DELETE, CONNECT, TRACE """
        return self.http_server_request.method

    @property
    def uri(self):
        """ The uri of the request. For example 'http://www.somedomain.com/somepath/somemorepath/somresource.foo?someparam=32&someotherparam=x """
        return self.http_server_request.uri   

    @property
    def path(self):
        """ The path part of the uri. For example /somepath/somemorepath/somresource.foo """
        return self.http_server_request.path    

    @property
    def query(self):
        """ The query part of the uri. For example someparam=32&someotherparam=x """
        return self.http_server_request.query

    @property
    def params(self):
        """ The request parameters as a dictionary """
        if self.params_dict is None:
            self.params_dict = map_from_java(self.http_server_request.params())
        return self.params_dict

    @property
    def response(self):
        """ The response HttpServerResponse object."""
        return self.http_server_response

    @property
    def headers(self):
        """ The request headers as a dictionary """
        if self.headers_dict is None:
            self.headers_dict = map_from_java(self.http_server_request.headers())
        return self.headers_dict

    def body_handler(self, handler):
        """ Set the body handler for this request, the handler receives a single Buffer object as a parameter. 
        This can be used as a decorator. 

        Keyword arguments:
        handler -- a handler that is called when the body has been received. The handler is wrapped in a BufferHandler.

        """
        self.http_server_request.bodyHandler(BufferHandler(handler))

class HttpServerResponse(object):
    """Encapsulates a server-side HTTP response.

    An instance of this class is created and associated to every instance of HttpServerRequest that is created.

    It allows the developer to control the HTTP response that is sent back to the client for the corresponding HTTP
    request. It contains methods that allow HTTP headers and trailers to be set, and for a body to be written out
    to the response.

    It also allows a file to be streamed by the kernel directly from disk to the outgoing HTTP connection,
    bypassing user space altogether (where supported by the underlying operating system). This is a very efficient way of
    serving files from the server since buffers do not have to be read one by one from the file and written to the outgoing
    socket. 

    """
    def __init__(self, http_server_response):
        self.http_server_response = http_server_response

    def get_status_code(self):
        """ Get the status code of the response. """
        return self.http_server_response.statusCode

    def set_status_code(self, code):
        """ Set the status code of the response. Default is 200 """
        self.http_server_response.statusCode = code

    status_code = property(get_status_code, set_status_code)

    def get_status_message(self):
        """ Get the status message the goes with status code """
        return self.http_server_response.statusMessage

    def set_status_message(self, message):
        """ Set the status message for a response """
        self.http_server_response.statusMessage = message

    status_message = property(get_status_message, set_status_message)

    @property
    def headers(self):
        """ Get a copy of the reponse headers as a dictionary """
        return map_from_java(self.http_server_response.headers())

    def put_header(self, key, value):
        """ Inserts a header into the response.

        Keyword arguments
        key -- The header key
        value -- The header value.
        
        returns HttpServerResponse so multiple operations can be chained.
        """
        self.http_server_response.putHeader(key, value)
        return self

    @property
    def trailers(self):
        """ Get a copy of the trailers as a dictionary """
        return map_from_java(self.http_server_response.trailers())

    def put_trailer(self, key, value):
        """ Inserts a trailer into the response. 

        Keyword arguments
        key -- The header key
        value -- The header value.
        
        returns HttpServerResponse so multiple operations can be chained.

        """
        self.http_server_response.putTrailer(key, value)
        return self

    def write_buffer(self, buffer, handler=None):
        """ Write a buffer to the response. The handler (if supplied) will be called when the buffer has actually been written to the wire.

        Keyword arguments
        buffer -- The buffer to write
        handler -- The handler to be called when writing has been completed. It is wrapped in a DoneHandler (default None)
        
        returns a HttpServerResponse so multiple operations can be chained.
        """
        if handler is None:
            self.http_server_response.writeBuffer(buffer._to_java_buffer())
        else:
            self.http_server_response.writeBuffer(buffer._to_java_buffer(), DoneHandler(handler))
        return self

    def write_str(self, str, enc="UTF-8", handler=None):
        """ Write a String to the response. The handler will be called when the String has actually been written to the wire.

        Keyword arguments
        str -- The string to write
        enc -- Encoding to use.

        handler -- The handler to be called when writing has been completed. It is wrapped in a DoneHandler (default None)
        
        returns a HttpServerResponse so multiple operations can be chained.
        """
        if handler is None:
            self.http_server_response.write(str, enc)
        else:
            self.http_server_response.write(str, enc, DoneHandler(handler)) 
        return self

    def send_file(self, path):
        """ Tell the kernel to stream a file directly from disk to the outgoing connection, bypassing userspace altogether
        (where supported by the underlying operating system. This is a very efficient way to serve files.

        Keyword arguments
        path -- Path to file to send.

        returns a HttpServerResponse so multiple operations can be chained.
        """
        self.http_server_response.sendFile(path)
        return self

    def set_chunked(self, val):
        """ Sets whether this response uses HTTP chunked encoding or not.

        Keyword arguments
        val -- If val is true, this response will use HTTP chunked encoding, and each call to write to the body
        will correspond to a new HTTP chunk sent on the wire. If chunked encoding is used the HTTP header
        'Transfer-Encoding' with a value of 'Chunked' will be automatically inserted in the response.

        If chunked is false, this response will not use HTTP chunked encoding, and therefore if any data is written the
        body of the response, the total size of that data must be set in the 'Content-Length' header before any
        data is written to the response body.
        An HTTP chunked response is typically used when you do not know the total size of the request body up front.
        
        returns a HttpServerResponse so multiple operations can be chained.
        """
        self.http_server_response.setChunked(val)
        return self

    def get_chunked(self):
        """ Get whether this response uses HTTP chunked encoding or not. """
        return self.http_server_response.getChunked()        

    chunked = property(get_chunked, set_chunked)

    def end(self, data=None):
        """ Ends the response. If no data has been written to the response body, the actual response won't get written until this method gets called.
        Once the response has ended, it cannot be used any more, and if keep alive is true the underlying connection will
        be closed.

        Keywords arguments
        data -- Optional String or Buffer to write before ending the response

        """
        if data is None:
            self.http_server_response.end()
        else:
            self.http_server_response.end(data)

    def close(self):
        """ Close the underlying TCP connection """
        self.http_server_response.close()

class WebSocket(object):
    """ Encapsulates an HTML 5 Websocket.

    Instances of this class are created by an HttpClient instance when a client succeeds in a websocket handshake with a server.
    Once an instance has been obtained it can be used to s or receive buffers of data from the connection,
    a bit like a TCP socket.
    """
    def __init__(self, websocket):
        self.websocket = websocket

    def write_binary_frame(self, buffer):
        """ 
        Write data to the websocket as a binary frame 

        Keyword arguments
        buffer -- Buffer data to write to socket.

        """
        self.websocket.writeBinaryFrame(buffer)

    def write_text_frame(self, text):
        """ 
        Write data to the websocket as a text frame 

        Keyword arguments
        text -- text to write to socket
        """
        self.websocket.writeTextFrame(text)

    def close(self):
        """ Close the websocket """
        self.websocket.close()

    def closed_handler(self, handler):
        """ Set a closed handler on the connection, the handler receives a no parameters. 
        This can be used as a decorator. 

        Keyword arguments
        handler - The handler to be called when writing has been completed. It is wrapped in a ClosedHandler.
        """
        self.websocket.closedHandler(ClosedHandler(handler))

class ServerWebSocket(WebSocket):
    """ Instances of this class are created when a WebSocket is accepted on the server.
    It extends WebSocket and adds methods to reject the WebSocket and an
    attribute for the path.

    """
    def __init__(self, websocket):
        self.websocket = websocket

    def reject(self):
        """ Reject the WebSocket. Sends 404 to client """
        self.websocket.reject()

    @property
    def path(self):
        """ The path the websocket connect was attempted at. """
        return self.websocket.path

class HttpServerRequestHandler(org.vertx.java.core.Handler):
    """ A handler for Http Server Requests"""
    def __init__(self, handler):
        self.handler = handler

    def handle(self, req):
        """ Called when a request is being handled. Argument is a HttpServerRequest object """
        self.handler(HttpServerRequest(req))

class HttpClientResponseHandler(org.vertx.java.core.Handler):
    """ A handler for Http Client Responses"""
    def __init__(self, handler):
        self.handler = handler

    def handle(self, res):
        """ Called when a response is being handled. Argument is a HttpClientResponse object """
        self.handler(HttpClientResponse(res))

class ServerWebSocketHandler(org.vertx.java.core.Handler):
    """ A handler for WebSocket Server Requests"""
    def __init__(self, handler):
        self.handler = handler

    def handle(self, req):
        """ Calls the Handler with the ServerWebSocket when connected """
        self.handler(ServerWebSocket(req))

class WebSocketHandler(org.vertx.java.core.Handler):
    """ A handler for WebSocket  Requests"""
    def __init__(self, handler):
        self.handler = handler

    def handle(self, req):
        """ Calls the Handler with the WebSocket when connected """
        self.handler(WebSocket(req))