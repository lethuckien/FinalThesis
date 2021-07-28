
from mysql.connector import cursor
import requests
import json
import configparser
import map


config = configparser.ConfigParser()
config.read('config.ini')

src_url = config.get('source','src_url')
debug = config.getboolean('config', 'debug')

def query_connector(query, query_type='select'):
    headers = {
        # 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
        # 'Connection': 'Keep-Alive'
    }
    r = requests.get(src_url +'/connector.php?query='+query+'&query_type='+query_type.casefold(), headers=headers)
    if debug:
        print(debug)
        print(r.text)
    if query_type.casefold() == 'select':
        # return json.loads(r.text)
        try:
            return json.loads(r.text)
        except:
            return r.text
    if query_type.casefold() == 'insert':
        return r.text
    if query_type.casefold() == 'count':
        return int(next(iter(json.loads(r.text)[0].values())))




def construct_category():
    return {
        'id': None,
        'code': None,
        'active': True,
        'thumb_image': {
            'label': '',
            'url': '',
        },
        'name': '',
        'description': '',
        'short_description': '',
        'created_at': None,
        'updated_at': None,
        'category_group': list()
    }

def construct_product():
    return {
        'id': None,
        'code': None,
        'type': '',
        'is_child': False,
        'thumb_image': {
            'label': '',
            'url': '',
            'status': True,
        },
        'images': list(),
        'name': '',
        'sku': '',
        'description': '',
        'short_description': '',
        'tags': '',
        'price': 0.0000,
        'cost': 0.0000,
        'special_price': {
            'price': 0.0000,
            'start_date': '',
            'end_date': '',
        },
        'weight': 0.0000,
        'length': 0.0000,
        'width': 0.0000,
        'height': 0.0000,
        'status': True,
        'manage_stock': False,
        'qty': 0,
        'is_in_stock': True,
        'created_at': None,
        'updated_at': None,
        'categories': list(),
        'options': list(),
        'attributes': list(),
        'children': list(),
    }

def construct_customer():
    return {
        'phone': '',
        'id': None,
        'code': None,
        'note': '',
        'group_id': '',
        'username': '',
        'email': '',
        'password': '',
        'first_name': '',
        'middle_name': '',
        'last_name': '',
        'gender': '',
        'dob': '',
        'is_subscribed': False,
        'active': True,
        'created_at': None,
        'updated_at': '',
        'address': list(),
        'balance': 0.00
    }

def construct_customer_address():
    return {
        'address_1': '',
        'address_2': '',
        'city': '',
        'country': '',
        'state': '',
        'postcode': '',
        'phone': '',
        'company': '',
        'fax': '',
        'billing': False,
        'shipping': False,
    }


def construct_order():
    return {
        'id': None,
        'order_number': None,
        'code': None,
        'status': '',
        'tax': {
            'title': '',
            'amount': 0.0000,
            'percent': 0.0000,
        },
        'discount': {
            'code': '',
            'title': '',
            'amount': 0.0000,
            'percent': 0.0000,
        },
        'shipping': {
            'title': '',
            'amount': 0.0000,
            'percent': 0.0000,
        },
        'subtotal': {
            'title': '',
            'amount': 0.0000,
        },
        'total': {
            'title': '',
            'amount': 0.0000,
        },
        'currency': '',
        'created_at': None,
        'updated_at': None,
        'customer': dict(),
        'customer_address': dict(),
        'billing_address': dict(),
        'shipping_address': dict(),
        'payment': {
            'id': None,
            'code': None,
            'method': '',
            'title': ''
        },
        'items': list(),
    }


def construct_order_item():
    return {
        'id': None,
        'code': None,
        'product': {
            'id': None,
            'var_id': None,
            'code': None,
            'name': '',
            'sku': '',
        },
        'qty': 0,
        'price': 0.0000,
        'original_price': 0.0000,
        'tax_amount': 0.0000,
        'tax_percent': 0.0000,
        'discount_amount': 0.0000,
        'discount_percent': 0.0000,
        'subtotal': 0.0000,
        'total': 0.0000,
        'created_at': None,
        'updated_at': None,
    }


def construct_order_customer():
    return {
        'id': None,
        'code': None,
        'username': '',
        'email': '',
        'first_name': '',
        'middle_name': '',
        'last_name': '',
    }


def construct_order_address():
    return {
        'id': None,
        'code': None,
        'first_name': '',
        'middle_name': '',
        'last_name': '',
        'address_1': '',
        'address_2': '',
        'city': '',
        'country': '',
        'state': '',
        'postcode': '',
        'telephone': '',
        'company': '',
        'fax': '',
    }

def get_map_field_by_src(type = None, id_src = None, field = 'id_dest'):
    conn = map.get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT "+field+" FROM migration_map WHERE id_src = "+str(id_src)+" AND type = '"+str(type)+"'")
    response = cursor.fetchone()
    if response:
        return response[0]
    else:
        return False


def get_order_status_target(status):
    order_status = {
        "wc-cancelled": "refunded",
        "wc-completed": "paid",
        "wc-processing": "authorized",
        "wc-refunded": "refunded",
        "wc-on-hold": "authorized",
        "wc-failed": "voided",
        "draft": "voided",
        "wc-pending": "pending"
    }
    return order_status[status]

def get_order_status_target_shopify(status):
    order_status_shopify = {
        "wc-cancelled": "fulfilled",
        "wc-completed": "fulfilled",
        "wc-failed": "unfulfilled",
        "wc-on-hold": "unfulfilled",
        "wc-processing": "unfulfilled",
        "wc-refunded": "fulfilled",
        "draft": "unfulfilled",
        "wc-pending": "unfulfilled"
    }
    return order_status_shopify[status]