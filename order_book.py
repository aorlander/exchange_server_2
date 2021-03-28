from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from models import Base, Order
engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

session.query(Order).delete()
session.commit()

def list_orders():
    orders = session.query(Order).all()
    for o in session.query(Order):
        #if(o.buy_currency=="Ethereum"):
        #    fx=o.buy_amount/o.sell_amount
        #if(o.sell_currency=="Ethereum"):
        #    fx=o.sell_amount/o.buy_amount
        if o.filled == None:
            if o.creator_id != None:
                #print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (created by " + str(o.creator_id) + " )")
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + "  (created by " + str(o.creator_id) + " )")
            if o.creator_id == None:
                #print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) )
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency )
        if o.filled != None:
            if o.creator_id != None:
                #print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (created by " + str(o.creator_id)  + ", filled by " + str(o.counterparty_id) + ")")  
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + "  (created by " + str(o.creator_id)  + ", filled by " + str(o.counterparty_id) + ")")    
            if o.creator_id == None:
                #print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + ", FX= " + str(fx) + "  (filled by " + str(o.counterparty_id) + ")")      
                print(str(o.id) + ": SELL " + str(o.sell_amount) + " " + o.sell_currency + " / BUY " + str(o.buy_amount) + " " + o.buy_currency + "  (filled by " + str(o.counterparty_id) + ")")

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
            if(algo_in < algo_out):
                print("order: " + str(order.id))  
                print("Algo in = " + str(order.sell_amount ))
                print("Alg out on counterparty = " + str(order.counterparty[0].buy_amount))
                if order.counterparty[0].child:
                    print("Algo out on order.child = " + str(-order.counterparty[0].child[0].buy_amount) + "child is ID " + str(order.child[0].id))
                if order.child:
                    print("Algo in on order.child = " + str(-order.child[0].sell_amount))
                print( f"Algo profits = {algo_in-algo_out:.2f}" )
        if order.sell_currency == "Ethereum":
            eth_in += order.sell_amount
            eth_out += order.counterparty[0].buy_amount 
            if order.counterparty[0].child:
                eth_out -= order.counterparty[0].child[0].buy_amount
            if order.child:
                eth_in -= order.child[0].sell_amount
            if(eth_in < eth_out):
                print("order: " + str(order.id))
                print("Eth in = " + str(order.sell_amount))
                print("Eth out on counterparty = " + str(order.counterparty[0].buy_amount ))
                if order.counterparty[0].child:
                    print("Eth out on order.child = " + str(-order.counterparty[0].child[0].buy_amount) + "child is ID " + str(order.child[0].id))
                if order.child:
                    print("Eth in on order.child = " + str(-order.child[0].sell_amount))
                print( f"Eth profits = {eth_in-eth_out:.2f}" )
                

    #print("Eth in = " + str(eth_in) + ", Eth out = " + str(eth_out) + ", Eth profits = " + str(eth_in-eth_out))
    #print("Algo in = " + str(algo_in) + ", Algo out = " + str(algo_out) + ", Algo profits = " + str(algo_in-algo_out))
    print( f"Eth profits = {eth_in-eth_out:.2f}" )
    print( f"Algo profits = {algo_in-algo_out:.2f}" )
    return 0

def check_currency(existing_order, order):
    if(existing_order.filled == None):
        if(existing_order.buy_currency == order.sell_currency):
                if(existing_order.sell_currency == order.buy_currency):
                    if(existing_order.sell_amount / existing_order.buy_amount >= order.buy_amount/order.sell_amount):
                        return True
    return False

def get_optimal_match(order):
    optimal = -1
    max_profit = 0
    ccy_in = order.sell_amount
    for existing_order in session.query(Order):
        if( (existing_order.filled == None) & (check_currency(existing_order, order) == True) & (existing_order.id != order.id) ):
            ccy_out = existing_order.buy_amount
            profit = ccy_in-ccy_out
            if (existing_order.sell_amount < order.buy_amount):
                ccy_in -= order.sell_amount - existing_order.buy_amount
                ccy_out -= order.buy_amount - existing_order.sell_amount
            if(profit>max_profit):
                max_profit=profit
                optimal = existing_order
    return optimal

def match_order(existing_order, order):
    if (existing_order.sell_amount < order.buy_amount):
        print("\nMATCH : " + str(order.id) + " with " + str(existing_order.id) )
        existing_implied_fx=existing_order.buy_amount/existing_order.sell_amount
        parent_implied_fx= order.buy_amount/order.sell_amount
        remaining_sell_amt = order.sell_amount - existing_order.buy_amount
        remaining_buy_amt = order.buy_amount - existing_order.sell_amount
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
        print("created: SELL " + str(derived_order.sell_amount) + " " + derived_order.sell_currency + " / BUY " + str(derived_order.buy_amount) + " " + derived_order.buy_currency)
    return 0

def process_order(order):
    current_order = Order( sender_pk=order['sender_pk'], receiver_pk=order['receiver_pk'], buy_currency=order['buy_currency'], sell_currency=order['sell_currency'], buy_amount=order['buy_amount'], sell_amount=order['sell_amount'])
    current_order.timestamp = datetime.now()
    session.add(current_order)
    session.commit()
    if(get_optimal_match(current_order) != -1):
        match_order(get_optimal_match(current_order), current_order)
    pass