"""XML Sitemap and Sitemap Index parser."""
from __future__ import annotations 
import xml .etree .ElementTree as ET 
from typing import List ,Optional 
from pydantic import BaseModel 
class SitemapEntry (BaseModel ):
    loc :str 
    lastmod :Optional [str ]=None 
    changefreq :Optional [str ]=None 
    priority :Optional [float ]=None 
class SitemapResult (BaseModel ):
    is_index :bool =False 
    urls :List [SitemapEntry ]=[]
    sub_sitemaps :List [str ]=[]
class SitemapParser :
    """Parses standard XML sitemaps and sitemap index manifests."""
    @staticmethod 
    def _strip_ns (tag :str )->str :
        """Strip XML namespace prefix from element tag."""
        return tag .split ("}",1 )[-1 ]if "}"in tag else tag 
    @classmethod 
    def parse (cls ,xml_text :str )->SitemapResult :
        """Parse raw XML string into a SitemapResult object."""
        result =SitemapResult ()
        if not xml_text or not xml_text .strip ():
            return result 
        try :
            root =ET .fromstring (xml_text .strip ())
        except ET .ParseError :
            return result 
        root_tag =cls ._strip_ns (root .tag ).lower ()
        if root_tag =="sitemapindex":
            result .is_index =True 
            for elem in root :
                if cls ._strip_ns (elem .tag ).lower ()=="sitemap":
                    loc =None 
                    for child in elem :
                        if cls ._strip_ns (child .tag ).lower ()=="loc"and child .text :
                            loc =child .text .strip ()
                    if loc :
                        result .sub_sitemaps .append (loc )
            return result 
        if root_tag =="urlset":
            for elem in root :
                if cls ._strip_ns (elem .tag ).lower ()=="url":
                    entry_data ={}
                    for child in elem :
                        tag_name =cls ._strip_ns (child .tag ).lower ()
                        text_val =child .text .strip ()if child .text else None 
                        if text_val :
                            if tag_name =="loc":
                                entry_data ["loc"]=text_val 
                            elif tag_name =="lastmod":
                                entry_data ["lastmod"]=text_val 
                            elif tag_name =="changefreq":
                                entry_data ["changefreq"]=text_val 
                            elif tag_name =="priority":
                                try :
                                    entry_data ["priority"]=float (text_val )
                                except ValueError :
                                    pass 
                    if "loc"in entry_data :
                        result .urls .append (SitemapEntry (**entry_data ))
        return result 
