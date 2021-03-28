from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from models import Base, Order
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def list_orders():
    orders = session.query(Order).all()
    for o in session.query(Order):
        if(o.buy_currency=="Ethereum"):
            fx=o.buy_amount/o.sell_amount
        if(o.sell_currency=="Ethereum"):
            fx=o.sell_amount/o.buy_amount
        if o.filled == None:
            if o.creator_id != None:
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (created by " + str(o.creator_id) + " )")
            if o.creator_id == None:
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) )
        if o.filled != None:
            if o.creator_id != None:
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (created by " + str(o.creator_id)  + ", filled by " + str(o.counterparty_id) + ")")      
            if o.creator_id == None:
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (filled by " + str(o.counterparty_id) + ")")      

def calc_net_profits():
    print(" ")
    eth_in = 0
    eth_out = 0
    algo_in = 0
    algo_out = 0
    orders = session.query(Order).filter(Order.filled != "").all()
    for order in orders:
        if order.sell_currency == "Algorand":
            algo_in += order.sell_amount 
            algo_out += order.counterparty[0].buy_amount
            if order.counterparty[0].child:
                algo_out -= order.counterparty[0].child[0].buy_amount
            if order.child:
                algo_in -= order.child[0].sell_amount
        if order.sell_currency == "Ethereum":
            eth_in += order.sell_amount
            eth_out += order.counterparty[0].buy_amount 
            if order.counterparty[0].child:
                eth_out -= order.counterparty[0].child[0].buy_amount
            if order.child:
                eth_in -= order.child[0].sell_amount
    print( f"Eth profits = {eth_in-eth_out:.2f}" )
    print( f"Algo profits = {algo_in-algo_out:.2f}" )
    return 0

def calc_net_deposits():
    algo_total_in = sum( [order.sell_amount for order in session.query(Order).filter(Order.creator == None).all() if order.sell_currency == "Algorand" ] )
    eth_total_in = sum( [order.sell_amount for order in session.query(Order).filter(Order.creator == None).all() if order.sell_currency == "Ethereum" ] )
    algo_unfilled_in = sum( [order.sell_amount for order in session.query(Order).filter(Order.filled == None).all() if order.sell_currency == "Algorand" ] )
    eth_unfilled_in = sum( [order.sell_amount for order in session.query(Order).filter(Order.filled == None).all() if order.sell_currency == "Ethereum" ] )
    print( f"Eth in = {eth_total_in-eth_unfilled_in:.2f}" )
    print( f"Algo in = {algo_total_in-algo_unfilled_in:.2f}" )
    return 0

def payouts_from_exchange():
    eth_out = 0
    algo_out = 0
    orders = session.query(Order).filter(Order.filled != "").all() #Get all filled orders
    for order in orders:
        if order.sell_currency == "Algorand":
            eth_out += order.counterparty[0].buy_amount
            if order.counterparty[0].child:
                eth_out -= order.counterparty[0].child[0].buy_amount
        if order.sell_currency == "Ethereum":
            algo_out += order.counterparty[0].buy_amount
            if order.counterparty[0].child:
                algo_out -= order.counterparty[0].child[0].buy_amount
    print( f"Eth out = {eth_out:.2f}" )
    print( f"Algo out = {algo_out:.2f}" )
    return 0

# Check if there are any existing orders that match. Given new_order and existing order, to match all of the following requirements must be fulfilled:
#      1) existing_order.filled must be None
#      2) existing_order.buy_currency == order.sell_currency
#      3) existing_order.sell_currency == order.buy_currency
#      4) The implied exchange rate of the new order must be at least that of the existing order 
#      5) The buy / sell amounts need not match exactly
#      6) Each order should match at most one other
def check_match(existing_order, order):
    if(order.filled==None):
        if(existing_order.buy_currency == order.sell_currency):
            if(existing_order.sell_currency == order.buy_currency):
                if(existing_order.sell_amount / existing_order.buy_amount >= order.buy_amount/order.sell_amount):
                     return True
    return False


# If a match is found between order and existing_order:
#      – Set the filled field to be the current timestamp on both orders
#      – Set counterparty_id to be the id of the other order
#      – If one of the orders is not completely filled (i.e. the counterparty’s sell_amount is less than buy_amount):
#            -Create a new order for remaining balance
#            -The new order should have the created_by field set to the id of its parent order
#            -The new order should have the same pk and platform as its parent order
#            -The sell_amount of the new order can be any value such that the implied exchange rate of the new order is at least that of the old order (i.e., B/S on the new order must be at least the B/S on the order that created it)
#            -You can then try to fill the new order
def match_order(existing_order, order):  
    if (existing_order.sell_amount < order.buy_amount):
        #print("\n current: SELL " + str(order.sell_amount) + " " + order.sell_currency + " / BUY " + str(order.buy_amount) + " " + order.buy_currency)
        remaining_buy_amt = order.buy_amount - existing_order.sell_amount
        remaining_sell_amt = order.sell_amount - existing_order.buy_amount
        derived_implied_fx=remaining_buy_amt/remaining_sell_amt
        #print("\n order FX = " + str(parent_implied_fx)  + " // existing FX = " + str(existing_implied_fx) + " // derived FX = " + str(derived_implied_fx))
        derived_order = Order (
            creator_id=order.id, 
            sender_pk=order.sender_pk,
            receiver_pk=order.receiver_pk, 
            buy_currency=order.buy_currency, 
            sell_currency=order.sell_currency, 
            buy_amount=remaining_buy_amt, 
            sell_amount= remaining_sell_amt)
        derived_order.timestamp = datetime.now()
        derived_order.relationship = (derived_order.id, order.id)
        session.add(derived_order)
        session.commit()
        existing_order.filled = order.timestamp 
        order.filled = order.timestamp
        existing_order.counterparty_id = order.id
        order.counterparty_id = existing_order.id
        existing_implied_fx=existing_order.buy_amount/existing_order.sell_amount
        parent_implied_fx= order.buy_amount/order.sell_amount
        #print("created: SELL " + str(child_order.sell_amount) + " " + child_order.sell_currency + " / BUY " + str(child_order.buy_amount) + " " + child_order.buy_currency)
    return 0


#Your solution should be in a file called ‘order_book.py’ and it should contain a method 'process_order(order)'. The function ‘process_order’ takes a single argument, a dictionary object containing the 6 fields above.
def process_order(order):
    #Insert the order into the database. 
    current_order = Order( sender_pk=order['sender_pk'], receiver_pk=order['receiver_pk'], buy_currency=order['buy_currency'], sell_currency=order['sell_currency'], buy_amount=order['buy_amount'], sell_amount=order['sell_amount'])
    current_order.timestamp = datetime.now()
    session.add(current_order)
    session.commit()
    #Check against existing orders for matches.
    for existing_order in session.query(Order).filter(Order.filled == None):
        if(check_match(existing_order, current_order)==True):
            match_order(existing_order, current_order)

    pass