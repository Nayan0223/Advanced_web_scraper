import pytest 
from scraper .models import HeadingItem ,LinkItem ,PageData ,ProductItem ,QuoteItem ,ScrapeResponse 
def test_product_item_price_parsing ():
    p1 =ProductItem (title ="Sample Book",price ="£19.99",url ="https://example.com/b1")
    assert p1 .price ==19.99 
    p2 =ProductItem (title ="Another Book",price =25.5 ,url ="https://example.com/b2")
    assert p2 .price ==25.5 
    p3 =ProductItem (title ="No Price",price ="",url ="https://example.com/b3")
    assert p3 .price is None 
def test_scrape_response_success_property ():
    res_ok =ScrapeResponse (url ="https://example.com",status_code =200 ,html ="<html></html>")
    assert res_ok .is_success is True 
    res_err =ScrapeResponse (url ="https://example.com",status_code =500 ,error ="Server error")
    assert res_err .is_success is False 
def test_quote_item_schema ():
    quote =QuoteItem (text ="Stay hungry, stay foolish.",author ="Steve Jobs",tags =["life","wisdom"])
    assert quote .author =="Steve Jobs"
    assert "wisdom"in quote .tags 
