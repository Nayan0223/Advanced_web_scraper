from scraper .anti_detection .headers import generate_realistic_headers 
from scraper .anti_detection .proxy import ProxyManager 
from scraper .anti_detection .user_agents import get_random_user_agent 
def test_user_agent_generation ():
    ua_desktop =get_random_user_agent ("desktop")
    assert "Mozilla"in ua_desktop 
    ua_mobile =get_random_user_agent ("mobile")
    assert "Mozilla"in ua_mobile 
def test_realistic_headers_generation ():
    headers =generate_realistic_headers ()
    assert "User-Agent"in headers 
    assert "Accept-Language"in headers 
    assert "Connection"in headers 
def test_proxy_manager_rotation_and_health ():
    proxies =["http://proxy1:8080","http://proxy2:8080"]
    pm =ProxyManager (proxies =proxies ,strategy ="round_robin",max_failures =2 )
    assert pm .get_proxy ()=="http://proxy1:8080"
    assert pm .get_proxy ()=="http://proxy2:8080"
    assert pm .get_proxy ()=="http://proxy1:8080"
    pm .report_failure ("http://proxy1:8080")
    pm .report_failure ("http://proxy1:8080")
    assert pm .healthy_proxies ==["http://proxy2:8080"]
    assert pm .get_proxy ()=="http://proxy2:8080"
