from flask import Flask, render_template, request
import requests
import json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_socketio import SocketIO
from flask_socketio import send, emit


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////media/singham/e1e50bd4-08fa-4ffd-a015-a73c293eaafe/lepy-backup/lokesh/kapil-stock-project/database.db'
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
db = SQLAlchemy(app)

db.engine.execute('''CREATE TABLE IF NOT EXISTS BOorder (id INTEGER PRIMARY KEY AUTOINCREMENT, symbolName TEXT, exchange TEXT, quantity TEXT, price TEXT, transactionType TEXT, orderType TEXT, 
                disclosedQuantity TEXT, priceType TEXT, triggerPrice TEXT, orderValidity TEXT, productType TEXT, squareOffValue TEXT, stopLossValue TEXT, valueType TEXT, trailingStopLoss TEXT,
                is_order_placed TINYINT, orderNumber TEXT, status TEXT, create_at DATETIME, updated_at DATETIME)''')
r = requests.post('https://api.stocknote.com/login', data=json.dumps({"userId": "DJ32983", "password": "dawarka@1234", "yob": "1968"}),
                  headers={'Content-Type': 'application/json', 'Accept': 'application/json'}).json()
header = {'Content-Type': 'application/json', 'Accept': 'application/json', 'x-session-token': r['sessionToken']}


@app.route('/', methods=['GET', 'POST'])
def stock_view():
    if request.method == "POST":
        data = dict(request.form)
        query = f'''INSERT INTO BOorder (symbolName, exchange, quantity, price, transactionType, orderType, disclosedQuantity, priceType, triggerPrice, orderValidity, productType,
        squareOffValue, stopLossValue, valueType, trailingStopLoss, is_order_placed, create_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'''
        db.engine.execute(query, (data['symbolName'], data['exchange'], data['quantity'], data['price'], data['transactionType'], data['orderType'], data['disclosedQuantity'],
                                  data['priceType'], data['triggerPrice'], data['orderValidity'], data['productType'], data['squareOffValue'], data['stopLossValue'], data['valueType'],
                                  data['trailingStopLoss'], 0, datetime.now(), datetime.now()))
    return render_template('stock.html')


@socketio.on('connect')
def handle_my_custom_event():
    stock_price = requests.get('https://api.stocknote.com/option/optionChain?searchSymbolName=COPPER&exchange=MCX', headers=header).json()
    balance = requests.get('https://api.stocknote.com/limit/getLimits', headers=header).json()
    copper_list = []
    for i in stock_price['optionChainDetails']:
        copper_list.append({'tradingSymbol': i['tradingSymbol'], 'lastTradedPrice': i['lastTradedPrice'], 'underLyingSymbol': i['underLyingSymbol']})
    json_data = {'stock_price': copper_list, 'equityLimit': balance['equityLimit']['grossAvailableMargin'],
                 'commodityLimit': balance['commodityLimit']['grossAvailableMargin']}
    send(json_data)


@socketio.on('message')
def handle_my_custom_event(data):
    socketio.sleep(3)
    stock_price = requests.get('https://api.stocknote.com/option/optionChain?searchSymbolName=COPPER&exchange=MCX', headers=header).json()
    balance = requests.get('https://api.stocknote.com/limit/getLimits', headers=header).json()
    copper_list = []
    for i in stock_price['optionChainDetails']:
        data = db.engine.execute('''SELECT * FROM BOorder WHERE is_order_placed=0 ORDER BY id DESC LIMIT 1''').fetchone()
        print(data[1], i['tradingSymbol'], data[1] == i['tradingSymbol'], data[9], i['lastTradedPrice'].split('.')[0], data[9] == i['lastTradedPrice'].split('.')[0])
        if data[1] == i['tradingSymbol'] and data[9] == i['lastTradedPrice'].split('.')[0]:
            json_db_data = {'symbolName': data[1], 'exchange': data[2], 'quantity': data[3], 'price': data[4], 'transactionType': data[5], 'orderType': data[6], 'disclosedQuantity': data[7],
                            'priceType': data[8], 'orderValidity': data[10], 'productType': data[11], 'triggerPrice': data[4], 'squareOffValue': data[12],
                            'stopLossValue': data[13], 'valueType': data[14], 'trailingStopLoss': data[15]}
            order_place = requests.post('https://api.stocknote.com/order/placeOrderBO', data=json.dumps(json_db_data), headers=header)
            print(order_place.json(), order_place.status_code)
        copper_list.append({'tradingSymbol': i['tradingSymbol'], 'lastTradedPrice': i['lastTradedPrice'], 'underLyingSymbol': i['underLyingSymbol']})
    json_data = {'stock_price': copper_list, 'equityLimit': balance['equityLimit']['grossAvailableMargin'],
                 'commodityLimit': balance['commodityLimit']['grossAvailableMargin']}
    emit('message', json_data, broadcast=True, include_self=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
