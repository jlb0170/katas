import pytest
from engine import Engine, Order, Dir, the
import pprint

@pytest.fixture
def engine():
    return Engine()

index = 0
def order(engine, raw):
    global index
    index += 1
    return engine.add_order_s(f'{index},{raw}')

def test_order_parse(engine):
    order = engine.order('1,BUY,10,99.0\n')
    assert order.order_id == '1'
    assert order.dir == Dir.BUY
    assert the(order.needs).quantity == 10
    assert order.price == 99.0


def test_add_orders_to_book(engine):

    buy_at_99 = order(engine, 'BUY,10,99.0')
    assert 1 == len(engine.buys())
    assert 0 == len(engine.sells())
    buy_at_100 = order(engine, 'BUY,10,100.0')
    assert 2 == len(engine.buys())

    assert 0 == len(engine.fills)

    sell = order(engine, 'SELL,10,99.5')
    assert 1 == len(engine.buys())
    assert 0 == len(engine.sells())
    assert 1 == len(engine.fills)

    assert buy_at_99 is engine.buys()[0]

def test_partial_fill_quantity_copies_and_reduces_book_quantity(engine):
    order(engine, 'BUY,10,99.5')
    order(engine, 'SELL,7,99.5')
    order(engine, 'SELL,3,99.5')

    assert not engine.all_orders()
    assert [7, 3] == [f.quantity for f in engine.fills]
    
def test_partial_fill_quantity_copies_and_reduces_book_quantity_flipped(engine):
    
    order(engine, 'SELL,3,99.5')
    order(engine, 'SELL,7,99.5')
    order(engine, 'BUY,10,99.5')

    assert not engine.all_orders()
    assert [3, 7] == [f.quantity for f in engine.fills]

def test_order_cancel(engine):
    order(engine, 'SELL,1,10.0')
    order2 = order(engine, 'SELL,3,10.0')
    order(engine, 'SELL,5,10.0')
    engine.add_order_s(f'{order2.order_id},CANCEL')

    assert [1,5] == [the(x.needs).quantity for x in engine.sells()]
    
# this passes; what happens when you modify quantity down after
# modifying the quantity up is not specified so is left ambiguous 
# currently. 
def test_order_modify_quantity_down(engine):
    order(engine, 'SELL,1,10.0')
    order2 = order(engine, 'SELL,3,10.0')
    order(engine, 'SELL,5,10.0')
    engine.add_order_s(f'{order2.order_id},MODIFY,2')

    assert [1,2,5] == [the(x.needs).quantity for x in engine.sells()]

def test_order_modify_quantity_up(engine):
    o1 = order(engine, 'BUY,5,99.0')
    o2 = order(engine, 'BUY,10,99.0')
    engine.add_order_s(f'{o1.order_id},MODIFY,10')
    o3 = order(engine, 'SELL,10,99.0')
    o4 = order(engine, 'SELL,10,99.0')

    summaries = [f.__repr__() for f in engine.fills]
    expected = [
            f'F<{o1.order_id} bought {o3.order_id} 5@99.0>',
            f'F<{o2.order_id} bought {o3.order_id} 5@99.0>',
            f'F<{o2.order_id} bought {o4.order_id} 5@99.0>',
            f'F<{o1.order_id} bought {o4.order_id} 5@99.0>'
            ]
    assert summaries == expected


def test_matching_by_order_id(engine):
    order(engine, 'SELL,1,10.0')
    o2 = order(engine, 'SELL,10,10.0')
    o3 = order(engine, 'SELL,13,10.0')
    
    assert engine.matching(o2.order_id) is o2
    assert engine.matching(o3.order_id) is o3

def test_acceptance(engine):
    o1 = order(engine, 'BUY,10,99.0')
    o2 = order(engine, 'BUY,25,99.25')
    o3 = order(engine, 'SELL,5,99.50')
    o4 = order(engine, 'SELL,20,99.75')
    o5 = order(engine, 'SELL,10,100.0')
    o6 = order(engine, 'SELL,10,99.5')
    o7 = order(engine, 'BUY,10,99.50')
    o8 = order(engine, 'BUY,30,99.75')

    summaries = [f.__repr__() for f in engine.fills]
    expected = [
            f'F<{o7.order_id} bought {o3.order_id} 5@99.5>',
            f'F<{o7.order_id} bought {o6.order_id} 5@99.5>',
            f'F<{o8.order_id} bought {o6.order_id} 5@99.5>',
            f'F<{o8.order_id} bought {o4.order_id} 20@99.75>'
            ]
    assert summaries == expected

