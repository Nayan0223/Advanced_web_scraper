"""Proxy manager with health tracking and rotation."""
from __future__ import annotations 
import random 
from typing import Dict ,List ,Literal ,Optional 
class ProxyManager :
    """Manages a pool of HTTP/HTTPS/SOCKS proxies with rotation and failure tracking."""
    def __init__ (
    self ,
    proxies :Optional [List [str ]]=None ,
    strategy :Literal ["round_robin","random"]="round_robin",
    max_failures :int =3 ,
    ):
        self .proxies :List [str ]=[p .strip ()for p in (proxies or [])if p .strip ()]
        self .strategy =strategy 
        self .max_failures =max_failures 
        self ._index =0 
        self ._failure_counts :Dict [str ,int ]={p :0 for p in self .proxies }
    @property 
    def has_proxies (self )->bool :
        return bool (self .healthy_proxies )
    @property 
    def healthy_proxies (self )->List [str ]:
        return [p for p in self .proxies if self ._failure_counts .get (p ,0 )<self .max_failures ]
    def get_proxy (self )->Optional [str ]:
        """Retrieve the next proxy according to rotation strategy."""
        healthy =self .healthy_proxies 
        if not healthy :
            return None 
        if self .strategy =="random":
            return random .choice (healthy )
        proxy =healthy [self ._index %len (healthy )]
        self ._index =(self ._index +1 )%len (healthy )
        return proxy 
    def report_success (self ,proxy :str )->None :
        """Reset failure counter on successful request."""
        if proxy in self ._failure_counts :
            self ._failure_counts [proxy ]=0 
    def report_failure (self ,proxy :str )->None :
        """Increment failure counter on failed request."""
        if proxy in self ._failure_counts :
            self ._failure_counts [proxy ]+=1 
