"""Data cleaning and normalization pipeline utilities."""
from __future__ import annotations 
import html 
import re 
from typing import Any ,Dict ,List ,Optional 
from urllib .parse import parse_qs ,urlencode ,urlparse ,urlunparse 
def clean_text (text :Optional [str ])->str :
    """Trim whitespace, decode HTML entities, and collapse internal spaces."""
    if not text :
        return ""
    unescaped =html .unescape (text )
    collapsed =re .sub (r"\s+"," ",unescaped )
    return collapsed .strip ()
def strip_tracking_params (url :str )->str :
    """Remove common marketing/tracking query parameters (utm_*, gclid, fbclid, etc.)."""
    try :
        parsed =urlparse (url )
        params =parse_qs (parsed .query ,keep_blank_values =True )
        tracking_keys ={
        "utm_source","utm_medium","utm_campaign","utm_term","utm_content",
        "fbclid","gclid","_hsenc","_hsmi","mc_cid","mc_eid"
        }
        cleaned_params ={k :v for k ,v in params .items ()if k .lower ()not in tracking_keys }
        new_query =urlencode (cleaned_params ,doseq =True )
        return urlunparse (parsed ._replace (query =new_query ))
    except Exception :
        return url 
def clean_item_dict (item :Dict [str ,Any ])->Dict [str ,Any ]:
    """Recursively clean string values in a dictionary."""
    cleaned :Dict [str ,Any ]={}
    for k ,v in item .items ():
        if isinstance (v ,str ):
            cleaned [k ]=clean_text (v )
        elif isinstance (v ,dict ):
            cleaned [k ]=clean_item_dict (v )
        elif isinstance (v ,list ):
            cleaned [k ]=[
            clean_text (elem )if isinstance (elem ,str )
            else clean_item_dict (elem )if isinstance (elem ,dict )
            else elem 
            for elem in v 
            ]
        else :
            cleaned [k ]=v 
    return cleaned 
