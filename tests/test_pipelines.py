import json 
import sqlite3 
from pathlib import Path 
from scraper .pipelines .cleaner import clean_text ,strip_tracking_params 
from scraper .pipelines .exporter import DataExporter 
from scraper .pipelines .validator import ItemPipeline 
from scraper .models import ProductItem 
def test_cleaner_utilities ():
    assert clean_text ("  Hello &amp; World  \n\t")=="Hello & World"
    url ="https://example.com/item?utm_source=twitter&utm_medium=cpc&id=42"
    cleaned =strip_tracking_params (url )
    assert "utm_source"not in cleaned 
    assert "id=42"in cleaned 
def test_validator_and_deduplicator ():
    pipeline =ItemPipeline (unique_key ="url")
    item1 ={"title":"Book 1","url":"https://example.com/1"}
    item2 ={"title":"Book 1 Duplicate","url":"https://example.com/1"}
    item3 ={"title":"Book 2","url":"https://example.com/2"}
    results =pipeline .process_items ([item1 ,item2 ,item3 ])
    assert len (results )==2 
    assert results [0 ]["title"]=="Book 1"
    assert results [1 ]["title"]=="Book 2"
def test_exporter_json_csv_sqlite (tmp_path :Path ):
    items =[
    {"id":1 ,"name":"Alpha","tags":["a","b"]},
    {"id":2 ,"name":"Beta","tags":["c"]},
    ]
    json_path =tmp_path /"data.json"
    DataExporter .export (items ,json_path ,file_format ="json")
    assert json_path .exists ()
    loaded_json =json .loads (json_path .read_text ())
    assert len (loaded_json )==2 
    csv_path =tmp_path /"data.csv"
    DataExporter .export (items ,csv_path ,file_format ="csv")
    assert csv_path .exists ()
    content =csv_path .read_text ()
    assert "Alpha"in content 
    db_path =tmp_path /"test.db"
    DataExporter .export (items ,db_path ,file_format ="sqlite",sqlite_table ="items")
    assert db_path .exists ()
    conn =sqlite3 .connect (db_path )
    cur =conn .cursor ()
    cur .execute ("SELECT name FROM items")
    rows =cur .fetchall ()
    assert len (rows )==2 
    assert rows [0 ][0 ]=="Alpha"
    conn .close ()
