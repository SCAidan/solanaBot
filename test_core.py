import pytest
from bot import core

def token(price=1,liq=50000,vol=100000,age=40):
    return dict(mint='fake-mint',symbol='TEST',price=price,liquidity=liq,volume=vol,age_min=age)

@pytest.fixture
def db(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DB',str(tmp_path/'test.db'))
    return core.connect()

def test_signal_filters():
    assert core.signal(token(liq=100),[]) is None
    assert core.signal(token(age=2),[]) is None
    assert core.signal(token(),[])=='new_pool_watch'
    assert core.signal(token(age=100),[0.9,0.95])=='momentum'

def test_buy_sell(db):
    assert core.buy(db,token(),'new_pool_watch',now=100000)
    assert not core.buy(db,token(),'new_pool_watch',now=100001)
    assert core.account(db)['cash']<500
    assert core.sell(db,'fake-mint',1.2,now=100100)
    assert not core.account(db)['positions']
    assert len(list(db.execute('SELECT * FROM trades')))==2

def test_stop(db):
    core.buy(db,token(),'new_pool_watch',now=100000)
    core.mark(db,token(price=0.8),now=100100)
    assert core.account(db)['positions']==[]

def test_position_cap(db):
    for i in range(3):
        t=token();t['mint']=f'mint-{i}'
        core.buy(db,t,'new_pool_watch',now=100000)
    assert len(core.account(db)['positions'])==2
