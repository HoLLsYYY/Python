"""HTTPS through Windows proxy settings and certificate store (WinHTTP)."""
import ctypes as c
from ctypes import wintypes as w
from urllib.parse import urlsplit


def request(method,url,data=None,*,destination=None,max_bytes=4*1024*1024,timeout_ms=15000):
    dll=c.WinDLL('winhttp',use_last_error=True)
    def api(name,args,result):
        fn=getattr(dll,name);fn.argtypes=args;fn.restype=result;return fn
    H=w.HANDLE;D=w.DWORD;P=c.c_void_p;S=w.LPCWSTR
    open_=api('WinHttpOpen',[S,D,S,S,D],H)
    connect=api('WinHttpConnect',[H,S,w.WORD,D],H)
    open_request=api('WinHttpOpenRequest',[H,S,S,S,S,P,D],H)
    timeouts=api('WinHttpSetTimeouts',[H,c.c_int,c.c_int,c.c_int,c.c_int],w.BOOL)
    send=api('WinHttpSendRequest',[H,S,D,P,D,D,c.c_size_t],w.BOOL)
    receive=api('WinHttpReceiveResponse',[H,P],w.BOOL)
    headers=api('WinHttpQueryHeaders',[H,D,S,P,c.POINTER(D),c.POINTER(D)],w.BOOL)
    read=api('WinHttpReadData',[H,P,D,c.POINTER(D)],w.BOOL)
    close=api('WinHttpCloseHandle',[H],w.BOOL)
    def checked(value):
        if not value:raise c.WinError(c.get_last_error())
        return value
    parts=urlsplit(url)
    if parts.scheme!='https':raise ValueError('HTTPS required')
    handles=[]
    try:
        session=checked(open_('ShyBear/2',4,None,None,0));handles.append(session)
        checked(timeouts(session,10000,10000,timeout_ms,timeout_ms))
        connection=checked(connect(session,parts.hostname,parts.port or 443,0));handles.append(connection)
        path=parts.path or '/'
        if parts.query:path+='?'+parts.query
        req=checked(open_request(connection,method,path,None,None,None,0x800000));handles.append(req)
        payload=data.encode('utf-8') if isinstance(data,str) else data
        body=c.create_string_buffer(payload) if payload is not None else None
        head='Content-Type: text/plain; charset=utf-8\r\n' if payload is not None else ''
        size=len(payload) if payload is not None else 0
        checked(send(req,head,len(head),body,size,size,0))
        checked(receive(req,None))
        status=D();length=D(c.sizeof(status))
        checked(headers(req,19|0x20000000,None,c.byref(status),c.byref(length),None))
        chunks=[];buffer=c.create_string_buffer(65536);count=D();total=0
        output=open(destination,'wb') if destination is not None and status.value==200 else None
        try:
            while True:
                checked(read(req,buffer,len(buffer),c.byref(count)))
                if not count.value:break
                total+=count.value
                if total>max_bytes:raise ValueError('Ответ сервера превышает допустимый размер')
                if output:output.write(buffer.raw[:count.value])
                else:chunks.append(buffer.raw[:count.value])
        finally:
            if output:output.close()
        return status.value,b''.join(chunks)
    finally:
        for handle in reversed(handles):close(handle)

