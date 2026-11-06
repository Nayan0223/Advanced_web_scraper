"""Parser for HTML metadata, OpenGraph, Twitter Cards, and Schema.org JSON-LD."""
from __future__ import annotations 
import json 
from typing import Any ,Dict ,List 
from urllib .parse import urljoin 
from bs4 import BeautifulSoup 
from scraper .models import PageMetadata 
def extract_metadata (soup :BeautifulSoup ,base_url :str )->PageMetadata :
    """Extract structured metadata from HTML BeautifulSoup tree."""
    meta =PageMetadata ()
    if soup .title and soup .title .string :
        meta .title =soup .title .get_text (" ",strip =True )
    for tag in soup .find_all ("meta"):
        name =tag .get ("name","").lower ()
        prop =tag .get ("property","").lower ()
        content =tag .get ("content","").strip ()
        if not content :
            continue 
        if name =="description"and not meta .description :
            meta .description =content 
        elif name =="keywords":
            meta .keywords =[k .strip ()for k in content .split (",")if k .strip ()]
        if prop .startswith ("og:"):
            meta .open_graph [prop ]=content 
            if prop =="og:title"and not meta .title :
                meta .title =content 
            elif prop =="og:description"and not meta .description :
                meta .description =content 
        if name .startswith ("twitter:"):
            meta .twitter_card [name ]=content 
    canonical_tag =soup .find ("link",rel ="canonical")
    if canonical_tag and canonical_tag .get ("href"):
        meta .canonical =urljoin (base_url ,canonical_tag ["href"].strip ())
    for script in soup .find_all ("script",type ="application/ld+json"):
        raw_text =script .string or script .get_text ()
        if not raw_text or not raw_text .strip ():
            continue 
        try :
            parsed =json .loads (raw_text .strip ())
            if isinstance (parsed ,list ):
                meta .json_ld .extend (parsed )
            elif isinstance (parsed ,dict ):
                meta .json_ld .append (parsed )
        except Exception :
            pass 
    return meta 
