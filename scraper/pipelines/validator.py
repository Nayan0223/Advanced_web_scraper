"""Pipeline validator and deduplicator."""
from __future__ import annotations 
import hashlib 
import json 
from typing import Any ,Dict ,List ,Optional ,Set ,Type 
from pydantic import BaseModel 
class ItemPipeline :
    """Processes, validates, and deduplicates items passing through scraping pipelines."""
    def __init__ (
    self ,
    item_model :Optional [Type [BaseModel ]]=None ,
    unique_key :Optional [str ]=None ,
    ):
        self .item_model =item_model 
        self .unique_key =unique_key 
        self ._seen_keys :Set [str ]=set ()
    def process_item (self ,item :Any )->Optional [Any ]:
        """Validate, deduplicate, and normalize a single item."""
        raw_dict :Dict [str ,Any ]
        if isinstance (item ,BaseModel ):
            raw_dict =item .model_dump ()
            model_instance =item 
        elif isinstance (item ,dict ):
            raw_dict =item 
            if self .item_model :
                try :
                    model_instance =self .item_model (**raw_dict )
                except Exception :
                    return None 
            else :
                model_instance =None 
        else :
            return item 
        if self .unique_key and self .unique_key in raw_dict :
            val =str (raw_dict [self .unique_key ])
            if val in self ._seen_keys :
                return None 
            self ._seen_keys .add (val )
        elif self .unique_key is None :
            item_hash =hashlib .sha256 (
            json .dumps (raw_dict ,sort_keys =True ,default =str ).encode ("utf-8")
            ).hexdigest ()
            if item_hash in self ._seen_keys :
                return None 
            self ._seen_keys .add (item_hash )
        return model_instance if model_instance is not None else raw_dict 
    def process_items (self ,items :List [Any ])->List [Any ]:
        """Process an entire batch of scraped items."""
        processed :List [Any ]=[]
        for item in items :
            res =self .process_item (item )
            if res is not None :
                processed .append (res )
        return processed 
