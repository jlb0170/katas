from enum import Enum
import math
import pprint
import re
import itertools

def the(foos):
    if len(foos) != 1:
        raise Exception(f'expected one element but got: {foos}')
    return foos[0]

class Dir(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

    def other_side(self):
        if self == Dir.BUY: return Dir.SELL
        return Dir.BUY

    def want_to_fill(self, desired_price, actual_price):
        if (self == Dir.BUY): # not more than $X/share
            return desired_price >= actual_price
        elif (self == Dir.SELL): # price must be at least $x/share
            return desired_price <= actual_price

class Fill:
    def __init__(self, book_order, in_order, quantity, price):
        self.book_order = book_order
        self.in_order = in_order
        self.quantity = quantity
        self.price = price

    def __repr__(self):
        buy, sell = self.book_order, self.in_order
        if self.in_order.dir == Dir.BUY:
            buy, sell = sell, buy
        return f'F<{buy.order_id} bought {sell.order_id} {self.quantity}@{self.price}>'

class Need:
    def __init__(self, order, arrival, quantity):
        self.order = order
        self.arrival = arrival
        self.quantity = quantity

    def __eq__(self, other):
        if isinstance(other, Need):
            return self.arrival == other.arrival and self.quantity == other.quantity
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __repr__(self):
        return f'N<{self.arrival} {self.quantity}>'

    def best_quantity(self, other):
        return min(self.quantity, other.quantity)

    def in_price(self, other):
        return self.order.dir.want_to_fill(self.order.price, other.order.price)

    def should_fill(self, other):
        return self.best_quantity(other) > 0 and self.in_price(other)

    def try_fill_against_counters(self, engine):
        result = False
        for counter_need in engine.counter_needs(self.order.dir):
            if (counter_need.should_fill(self)):
                engine.fills.append(counter_need.fill(self))
                did_fill = True
        return result


    def fill(self, other):
        fill = Fill(self.order, other.order, self.best_quantity(other), self.order.price)
        for o in [self, other]:
            o.quantity -= fill.quantity
            o.order.strip_zero_needs()
        return fill

class Order:
    def __init__(self, order_id, dir, quantity, price, arrival = 1000000):
        self.order_id = order_id
        self.dir = dir
        self.needs = []
        self.price = price
        self.fills = []
        self.add_need(arrival, quantity)

    def __eq__(self, other):
        if isinstance(other, Order):
            return self.order_id == other.order_id and self.dir == other.dir and self.needs == other.needs \
                    and math.isclose(self.price, other.price, rel_tol=0.001)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def decrement_needs_backward(self, new_quantity):
        # currently mod-downs the newest orders first, which seems consistent with prioritizing the 
        # newest mod-ups last; tests don't specify which way it should go yet.
        for n in sorted(self.needs, key = lambda n: -n.arrival): 
            decrement = min(n.quantity - new_quantity, n.quantity)
            n.quantity -= decrement
            new_quantity -= decrement
            if new_quantity <= 0:
                break

    def add_need(self, arrival, quantity):
        self.needs.append(Need(self, arrival, quantity))

    def strip_zero_needs(self):
        self.needs = [n for n in self.needs if n.quantity > 0]

    def other_side(self):
        return self.dir.other_side()

    def __str__(self):
        return repr(self)
    
    def __repr__(self):
        return f'{self.order_id}<{self.dir.name} {self.needs}@{self.price}: {[f.quantity for f in self.fills]}>'

    def process(self, engine):
        while True: 
            need = self.needs[0]
            did_fill = need.try_fill_against_counters(engine)
            if not(self.needs and did_fill):
                break

        engine.add_to_book(self)
        engine.strip_empty_orders()
        return self

class Cancel:
    def __init__(self, order_id):
        self.order_id = order_id

    def process(self, engine):
        engine.remove_matching(self.order_id)
        return self
    
class Modify:
    def __init__(self, raw, arrival):
        self.order_id, modify_unused, self.new_quantity = raw.split(',')
        self.new_quantity = int(self.new_quantity)
        self.arrival = arrival

    def process(self, engine):
        matching = engine.matching(self.order_id)
        need_total = sum(n.quantity for n in matching.needs)
        if self.new_quantity < need_total:
            matching.decrement_needs_backward(self.new_quantity)
        elif self.new_quantity > need_total:
            increment = self.new_quantity - need_total
            matching.add_need(self.arrival, increment)
            
        matching.strip_zero_needs()
        engine.strip_empty_orders();

        return self

def coalesce(items):
    for i in items:
        if i:
            return i

def flatten(lists):
    result = []
    for l in lists:
        result.extend(l)
    return result
    
class Engine:
    def __init__(self):
        self.orders = {
            Dir.BUY: {},
            Dir.SELL: {}
        }
        self.fills = []
        self.order_arrival = 0

    def strip_empty_orders(self):
        for dir in self.orders:
            orders = self.orders[dir]
            for order_id, order in list(orders.items()):
                if not order.needs:
                    del orders[order_id]

    def counter_needs(self, dir):
        counters = self.orders[dir.other_side()].values()
        counter_needs = flatten(c.needs for c in counters)
        return sorted(counter_needs, key = lambda counter_need: 
                [counter_need.order.price, counter_need.arrival])

    def prioritized(self, orders):
        return sorted(orders, key = lambda o: [o.price])

    def add_to_book(self, order):
        self.orders[order.dir][order.order_id] = order

    def order(self, raw):
        self.order_arrival += 1
        if raw.endswith('CANCEL'):
            return Cancel(raw.split(',')[0])
        elif re.search('MODIFY', raw):
            return Modify(raw, self.order_arrival)
        id, dir_s, quantity_s, price_s = raw.split(',')
        return Order(id, Dir[dir_s], int(quantity_s), float(price_s), self.order_arrival)

    def add(self, order):
        return order.process(self)

    def add_order_s(self, order_s):
        return self.add(self.order(order_s))

    def buys(self):
        return self.prioritized(self.dir_orders(Dir.BUY))

    def sells(self):
        return self.prioritized(self.dir_orders(Dir.SELL))

    def dir_orders(self, dir):
        return self.orders[dir].values()

    def all_orders(self):
        return flatten(self.dir_orders(dir) for dir in Dir)

    def remove_matching(self, order_id):
        for dir in self.orders:
            self.orders[dir].pop(order_id, None)
       
    def matching(self, order_id):
        return coalesce(self.orders[dir].get(order_id, None) for dir in Dir)

        

