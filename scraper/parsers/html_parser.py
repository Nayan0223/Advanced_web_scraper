"""Resilient HTML content and selector extractor."""
from __future__ import annotations 
import re 
from typing import Any ,Dict ,List ,Optional 
from urllib .parse import urldefrag ,urljoin ,urlparse 
from bs4 import BeautifulSoup ,Tag 
from scraper .models import HeadingItem ,ImageItem ,LinkItem ,PageData ,PageMetadata 
from scraper .parsers .metadata_parser import extract_metadata 
class HTMLParser :
    """Extracts structured and unstructured information from raw HTML documents."""
    def __init__ (self ,html :str ,base_url :str ):
        self .html =html or ""
        self .base_url =base_url 
        try :
            self .soup =BeautifulSoup (self .html ,"lxml")
        except Exception :
            self .soup =BeautifulSoup (self .html ,"html.parser")
    def clean_soup (self )->BeautifulSoup :
        """Return a copy of soup with noisy tags removed."""
        clean =BeautifulSoup (self .html ,"html.parser")
        for tag in clean (["script","style","noscript","svg","iframe","nav","footer"]):
            tag .decompose ()
        return clean 
    def extract_page_data (self )->PageData :
        """Extract full comprehensive PageData model."""
        metadata =extract_metadata (self .soup ,self .base_url )
        title =metadata .title or (self .soup .title .get_text (" ",strip =True )if self .soup .title else "")
        description =metadata .description 
        headings :List [HeadingItem ]=[]
        for tag in self .soup .find_all (["h1","h2","h3","h4","h5","h6"]):
            text =tag .get_text (" ",strip =True )
            if text :
                level =int (tag .name [1 ])
                headings .append (HeadingItem (level =level ,text =text ))
        clean =self .clean_soup ()
        content_root =clean .find ("main")or clean .find ("article")or clean .body or clean 
        raw_text =" ".join (content_root .stripped_strings )
        text =re .sub (r"\s+"," ",raw_text ).strip ()
        links :List [LinkItem ]=[]
        seen_links =set ()
        for a in self .soup .find_all ("a",href =True ):
            href =a ["href"].strip ()
            if not href or href .startswith (("mailto:","tel:","javascript:","#")):
                continue 
            abs_url ,_ =urldefrag (urljoin (self .base_url ,href ))
            if abs_url not in seen_links and urlparse (abs_url ).scheme in {"http","https"}:
                seen_links .add (abs_url )
                anchor_text =a .get_text (" ",strip =True )
                links .append (LinkItem (text =anchor_text ,url =abs_url ))
        images :List [ImageItem ]=[]
        seen_imgs =set ()
        for img in self .soup .find_all ("img",src =True ):
            src =img ["src"].strip ()
            if not src or src .startswith ("data:"):
                continue 
            abs_src =urljoin (self .base_url ,src )
            if abs_src not in seen_imgs :
                seen_imgs .add (abs_src )
                alt =img .get ("alt","").strip ()
                images .append (ImageItem (src =abs_src ,alt =alt ))
        return PageData (
        url =self .base_url ,
        title =title ,
        description =description ,
        headings =headings ,
        text =text [:20000 ],
        links =links ,
        images =images ,
        metadata =metadata ,
        )
    def select (self ,selector :str )->List [Tag ]:
        """Query elements using CSS selector."""
        return self .soup .select (selector )
    def select_one (self ,selector :str )->Optional [Tag ]:
        """Query single element using CSS selector."""
        return self .soup .select_one (selector )
    def extract_text (self ,selector :str ,default :str ="")->str :
        """Extract stripped text from a selector."""
        el =self .select_one (selector )
        return el .get_text (" ",strip =True )if el else default 
    def extract_attr (self ,selector :str ,attr :str ,default :str ="")->str :
        """Extract attribute from a selector."""
        el =self .select_one (selector )
        return el .get (attr ,default )if el else default 
