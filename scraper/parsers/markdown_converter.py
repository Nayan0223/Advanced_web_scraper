"""HTML to clean Markdown converter tailored for LLMs and AI ingestion."""
from __future__ import annotations 
import re 
from typing import Optional 
from urllib .parse import urljoin 
from bs4 import BeautifulSoup ,NavigableString ,Tag 
class MarkdownConverter :
    """Converts HTML documents into clean, token-efficient Markdown."""
    def __init__ (self ,base_url :str =""):
        self .base_url =base_url 
    def convert (self ,html :str )->str :
        """Convert raw HTML to formatted markdown."""
        if not html or not html .strip ():
            return ""
        soup =BeautifulSoup (html ,"html.parser")
        for tag in soup (["script","style","noscript","svg","iframe","nav","footer","form"]):
            tag .decompose ()
        root =soup .find ("article")or soup .find ("main")or soup .body or soup 
        md_lines =[]
        self ._process_element (root ,md_lines )
        raw_md ="\n".join (md_lines )
        cleaned_md =re .sub (r"\n{3,}","\n\n",raw_md )
        return cleaned_md .strip ()
    def _process_element (self ,element :Tag ,output :list [str ])->None :
        for child in element .children :
            if isinstance (child ,NavigableString ):
                text =str (child ).strip ()
                if text :
                    output .append (text )
                continue 
            if not isinstance (child ,Tag ):
                continue 
            tag_name =child .name .lower ()
            if tag_name in {"h1","h2","h3","h4","h5","h6"}:
                level =int (tag_name [1 ])
                text =child .get_text (" ",strip =True )
                if text :
                    output .append (f"\n{'#'*level } {text }\n")
            elif tag_name =="p":
                p_text =self ._render_inline (child )
                if p_text :
                    output .append (f"\n{p_text }\n")
            elif tag_name =="blockquote":
                q_text =child .get_text (" ",strip =True )
                if q_text :
                    output .append (f"\n> {q_text }\n")
            elif tag_name in {"ul","ol"}:
                output .append ("")
                is_ordered =tag_name =="ol"
                for idx ,li in enumerate (child .find_all ("li",recursive =False ),1 ):
                    li_text =self ._render_inline (li )
                    prefix =f"{idx }."if is_ordered else "-"
                    output .append (f"{prefix } {li_text }")
                output .append ("")
            elif tag_name =="pre":
                code_text =child .get_text ().strip ()
                output .append (f"\n```\n{code_text }\n```\n")
            elif tag_name =="table":
                self ._process_table (child ,output )
            elif tag_name in {"div","section","article","main"}:
                self ._process_element (child ,output )
            else :
                inline =self ._render_inline (child )
                if inline :
                    output .append (inline )
    def _render_inline (self ,element :Tag )->str :
        """Render inline elements like links, bold, italics."""
        parts =[]
        for child in element .children :
            if isinstance (child ,NavigableString ):
                parts .append (str (child ))
            elif isinstance (child ,Tag ):
                name =child .name .lower ()
                text =child .get_text ()
                if name =="a":
                    href =child .get ("href","")
                    if href and self .base_url :
                        href =urljoin (self .base_url ,href )
                    parts .append (f"[{text }]({href })"if href else text )
                elif name in {"strong","b"}:
                    parts .append (f"**{text }**")
                elif name in {"em","i"}:
                    parts .append (f"*{text }*")
                elif name =="code":
                    parts .append (f"`{text }`")
                else :
                    parts .append (self ._render_inline (child ))
        return re .sub (r"\s+"," ","".join (parts )).strip ()
    def _process_table (self ,table :Tag ,output :list [str ])->None :
        rows =table .find_all ("tr")
        if not rows :
            return 
        table_matrix =[]
        for tr in rows :
            cells =[c .get_text (" ",strip =True )for c in tr .find_all (["th","td"])]
            if cells :
                table_matrix .append (cells )
        if not table_matrix :
            return 
        max_cols =max (len (row )for row in table_matrix )
        normalized =[row +[""]*(max_cols -len (row ))for row in table_matrix ]
        output .append ("")
        header =normalized [0 ]
        output .append ("| "+" | ".join (header )+" |")
        output .append ("| "+" | ".join (["---"]*max_cols )+" |")
        for row in normalized [1 :]:
            output .append ("| "+" | ".join (row )+" |")
        output .append ("")
