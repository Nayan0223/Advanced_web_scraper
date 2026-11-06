"""Asynchronous rate limiter and politeness controller."""
from __future__ import annotations 
import asyncio 
import random 
import time 
from typing import Dict 
from urllib .parse import urlparse 
class AsyncRateLimiter :
    """Per-domain asynchronous politeness rate limiter with random jitter."""
    def __init__ (self ,delay_seconds :float =0.5 ,jitter_ratio :float =0.3 ):
        self .delay_seconds =delay_seconds 
        self .jitter_ratio =jitter_ratio 
        self ._last_access :Dict [str ,float ]={}
        self ._locks :Dict [str ,asyncio .Lock ]={}
    def _get_domain (self ,url :str )->str :
        try :
            return urlparse (url ).netloc .lower ()or "default"
        except Exception :
            return "default"
    async def wait_for (self ,url :str )->None :
        """Pause execution if necessary to respect domain politeness delay."""
        if self .delay_seconds <=0 :
            return 
        domain =self ._get_domain (url )
        if domain not in self ._locks :
            self ._locks [domain ]=asyncio .Lock ()
        async with self ._locks [domain ]:
            now =time .monotonic ()
            last_time =self ._last_access .get (domain ,0.0 )
            elapsed =now -last_time 
            jitter =self .delay_seconds *random .uniform (-self .jitter_ratio ,self .jitter_ratio )
            target_delay =max (0.05 ,self .delay_seconds +jitter )
            if elapsed <target_delay :
                wait_time =target_delay -elapsed 
                await asyncio .sleep (wait_time )
            self ._last_access [domain ]=time .monotonic ()
