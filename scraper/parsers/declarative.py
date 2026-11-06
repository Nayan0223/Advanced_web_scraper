"""Declarative YAML/JSON schema-driven web scraping engine."""
from __future__ import annotations 
import re 
from pathlib import Path 
from typing import Any ,Dict ,List ,Optional ,Union 
from urllib .parse import urljoin 
from bs4 import BeautifulSoup ,Tag 
import yaml 
from pydantic import BaseModel ,Field 
class FieldRule (BaseModel ):
    selector :str 
    attribute :Optional [str ]=None 
    field_type :str ="text"
    default :Any =None 
class DeclarativeSchema (BaseModel ):
    name :str ="custom_scraper"
    start_urls :List [str ]
    container :Optional [str ]=None 
    fields :Dict [str ,Union [str ,FieldRule ]]
    pagination :Optional [str ]=None 
    max_pages :int =1 
class DeclarativeScraper :
    """Parses HTML into dictionaries based on declarative CSS/XPath field rules."""
    def __init__ (self ,schema :DeclarativeSchema ):
        self .schema =schema 
        self ._parsed_fields :Dict [str ,FieldRule ]=self ._compile_fields (schema .fields )
    @classmethod 
    def from_file (cls ,path :Union [str ,Path ])->DeclarativeScraper :
        """Load schema from a YAML or JSON file."""
        file_path =Path (path )
        content =file_path .read_text (encoding ="utf-8")
        data =yaml .safe_load (content )
        schema =DeclarativeSchema (**data )
        return cls (schema )
    @staticmethod 
    def _compile_fields (fields :Dict [str ,Union [str ,FieldRule ]])->Dict [str ,FieldRule ]:
        compiled ={}
        for key ,val in fields .items ():
            if isinstance (val ,FieldRule ):
                compiled [key ]=val 
                continue 
            selector =val .strip ()
            field_type ="text"
            attribute =None 
            if "|"in selector :
                parts =selector .split ("|",1 )
                selector =parts [0 ].strip ()
                field_type =parts [1 ].strip ().lower ()
            if "@"in selector :
                parts =selector .split ("@",1 )
                selector =parts [0 ].strip ()
                attribute =parts [1 ].strip ()
            compiled [key ]=FieldRule (
            selector =selector ,
            attribute =attribute ,
            field_type =field_type ,
            )
        return compiled 
    def _extract_single_field (self ,element :Tag ,rule :FieldRule ,base_url :str )->Any :
        if rule .field_type =="list":
            tags =element .select (rule .selector )if rule .selector else [element ]
            if rule .attribute :
                return [t .get (rule .attribute ,"")for t in tags ]
            return [t .get_text (" ",strip =True )for t in tags ]
        target =element .select_one (rule .selector )if rule .selector else element 
        if not target :
            return rule .default 
        if rule .attribute :
            val =target .get (rule .attribute ,"")
            if rule .attribute in {"href","src"}:
                val =urljoin (base_url ,val )
            return val 
        raw_text =target .get_text (" ",strip =True )
        if rule .field_type =="int":
            digits =re .sub (r"[^\d-]","",raw_text )
            return int (digits )if digits else rule .default 
        if rule .field_type =="float":
            cleaned =re .sub (r"[^\d.-]","",raw_text )
            return float (cleaned )if cleaned else rule .default 
        return raw_text 
    def parse (self ,html :str ,base_url :str )->List [Dict [str ,Any ]]:
        """Extract items according to the declarative schema."""
        soup =BeautifulSoup (html ,"html.parser")
        items :List [Dict [str ,Any ]]=[]
        if self .schema .container :
            containers =soup .select (self .schema .container )
            for container in containers :
                item_data :Dict [str ,Any ]={"_url":base_url }
                for field_name ,rule in self ._parsed_fields .items ():
                    item_data [field_name ]=self ._extract_single_field (container ,rule ,base_url )
                items .append (item_data )
        else :
            item_data ={"_url":base_url }
            for field_name ,rule in self ._parsed_fields .items ():
                item_data [field_name ]=self ._extract_single_field (soup ,rule ,base_url )
            items .append (item_data )
        return items 
    def get_next_page (self ,html :str ,base_url :str )->Optional [str ]:
        """Extract next page pagination link if available."""
        if not self .schema .pagination :
            return None 
        soup =BeautifulSoup (html ,"html.parser")
        selector =self .schema .pagination 
        attr ="href"
        if "@"in selector :
            selector ,attr =selector .split ("@",1 )
        el =soup .select_one (selector .strip ())
        if el and el .get (attr .strip ()):
            return urljoin (base_url ,el [attr .strip ()])
        return None 
