from itertools import product
import basecart as bc
import requests
import configparser
import json

config = configparser.ConfigParser()
config.read('config.ini')
url = ''
api_pass = ''
if config.get('source', 'src_type') == 'shopify':
    url = config.get('source', 'src_url').strip('/')
    api_pass = config.get('source', 'api_pass')
else:
    url = config.get('target', 'tar_url').strip('/')
    api_pass = config.get('target', 'api_pass')

url_src = config.get('source', 'src_url').strip('/')

def api(endpoint, data=None, method='GET'):
    headers = {
        'X-Shopify-Access-Token': api_pass,
        'Content-Type': "application/json"
    }
    if method == 'GET':
        data = None
    r = requests.request(method, url + '/admin/api/2021-04/'+ endpoint, json=data, headers=headers)
    
    try:
        return json.loads(r.text)
    except:
        return r.text


def get_location_id():
    response = api('locations.json')
    if isinstance(response, dict):
        if response.get('locations'):
            return response['locations'][0]['id']
    return False

def category_import(category, category_ext, convert):
    post_data = {
        'custom_collection': {
            'title': convert['name'],
            'published': convert['active'],
            'body_html': convert['description'],
            'updated_at': convert['updated_at']

        }
    }
    if convert['thumb_image']['url']:
        post_data['custom_collection']['image'] = {
            'src': convert['thumb_image']['url'],
        }

    r = api('custom_collections.json', post_data, 'POST')

    if isinstance(r,dict):
        if r.get('custom_collection'):
            if r['custom_collection'].get('id'):
                return r['custom_collection'].get('id')
        else:
            print('Error: ' + str(r))
            return False
    else:
        print('Error: ' + str(r))
        return False
    

def product_import(product,product_ext,convert):
    product_id = False
    post_data = {
        'product': {
            'title': convert['name'],
            'body_html': convert['description'] if convert['description'] else convert['short_description'],
            'created_at': convert['created_at'],
            'updated_at': convert['updated_at'],
            'status': 'draft' if not convert['status'] else 'active',
            'tags': convert['tags']
        }
    }
    image_data = list()
    thumb_nail_data = {
        'src': convert['thumb_image']['url'],
        'position': 0
    }
    image_data.append(thumb_nail_data)
    for image in convert['images']:
        gallery_data = {
            'src': image['url']
        }
        image_data.append(gallery_data)
    post_data['product']['images'] = image_data

    product_api = api('products.json', post_data, 'post')
    if product_api.get('product'):
        if product_api['product'].get('id'):
            product_id = product_api['product'].get('id')
            variant_id = product_api['product']['variants'][0]['id']
    else:
        print('Error: ' + str(product_api))
        return False
    for category in convert['categories']:
        category_id = bc.get_map_field_by_src(type='category', id_src=category)
        if category_id:
            cat_post_data = {
                'collect': {
                    'collection_id': category_id,
                    'product_id': product_id
				}
            }
            r = api('collects.json', cat_post_data, 'POST')
            if not r.get('collect'):
                print('Error category product: ' + str(r))
    var_post_data = {
        'product': {
            'id': product_id,
            'variants': list(),
        }
    }
    options = list()
    option_check = False
    variant_img_map = dict()

    for child in convert['children']:
        variant_img_map[child['sku']] = child['thumb_image']['url']
        variant = {
            'product_id': product_id,
            'title': child['name'],
            'sku': child['sku'] if child['sku'] else convert['sku'],
            'price': child['price'],
            'cost': child['cost'] if child['cost'] else None,
            'inventory_policy': 'deny' if child['manage_stock'] else 'continue',
            'inventory_management': 'shopify' if child['manage_stock'] else None,
            'taxable': False,
        }
        i = 1
        for attribute in child['attributes']:
            if attribute['attribute_value']:
                variant['option'+str(i)] = attribute['attribute_value']
                i += 1
            else:
                variant['option'+str(i)] = 'No Value'
                i += 1
            if not option_check:
                option_data = dict()
                option_data['product_id'] = product_id
                option_data['values'] = list()
                option_data['name'] = attribute['attribute_name']
                option_data['values'] = attribute['all_values']
                options.append(option_data)
        var_post_data['product']['variants'].append(variant)
        option_check = True
    if options:
        var_post_data['product']['options'] = options
    if var_post_data['product']['variants']:
        r_var = api('products/'+str(product_id)+'.json', var_post_data, 'PUT')
        if not r_var.get('product'):
            print('Error variant product: ' + str(r_var))

        dup_img_map = dict()
        if isinstance(r_var,dict):
            if r_var.get('product'):
                if r_var['product'].get('variants'):
                    for variant in r_var['product']['variants']:
                        if variant_img_map.get(variant['sku']):
                            if dup_img_map.get(variant_img_map[variant['sku']]):
                                dup_img_map[variant_img_map[variant['sku']]].append(variant['id'])
                            else:
                                dup_img_map[variant_img_map[variant['sku']]] = list()
                                dup_img_map[variant_img_map[variant['sku']]].append(variant['id'])

        for img in dup_img_map:
            img_data = {
                'image': {
                    'src': img,
                    'variant_ids': dup_img_map[img]
                }
            }
            res = api('products/'+str(product_id)+'/images.json',img_data,'POST')
            if not res.get('image'):
                print('Error image child product: ' + str(res))

    if not convert['children']:
        variant_data = {
            'variant': {
                'id': variant_id,
                'price': convert['special_price']['price'] if convert['special_price']['price'] else convert['price'],
                'compare_at_price': convert['price'],
                'sku': convert['sku'],
                'inventory_management': 'shopify' if convert['manage_stock'] else None,
                'inventory_policy': 'deny' if convert['manage_stock'] else 'continue',
            },
        }
        variant_api = api('variants/'+str(variant_id)+'.json', variant_data, 'PUT')
        if not variant_api.get('variant'):
            print('Error variant: ' + str(variant_api))
        if convert['manage_stock']:
            location_id = get_location_id()
            if location_id:
                inventory_post = {
                    'location_id': location_id,
                    'inventory_item_id': product_api['product']['variants'][0]['inventory_item_id'],
                    'available': int(convert['qty']),
                }
                inventory_api = api('inventory_levels/set.json', inventory_post, 'POST')
                if not inventory_api.get('inventory_level'):
                    print('Error variant: ' + str(variant_api))
    return product_id, variant_id
    


def customer_import(customer,customer_ext,convert):
    customer_data = {
        "first_name": convert['first_name'],
        "last_name": convert['last_name'],
        "email": convert['email'],
        "verified_email": False,
        "accepts_marketing": True if convert['is_subscribed'] else False,
        "send_email_welcome": False,
        "created_at": convert['created_at'],
        "updated_at": convert['updated_at'],
        "addresses_attributes": list()
    }
    if convert['phone']:
        customer_data['phone'] = convert['phone']
    if convert['note']:
        customer_data['note'] = convert['note']
    
    for address in convert['address']:
        customer_address = {
            "address1": address['address_1'],
            "address2": address['address_2'],
            "city": address['city'],
            "province": '',
            "province_code": '',
            "phone": address['phone'],
            "zip": address['postcode'],
            "last_name": convert['last_name'],
            "first_name": convert['first_name'],
            "country": address['country'],
            "company": address['company']
        }
        if address['shipping']:
            customer_address['default'] = True
        customer_data['addresses_attributes'].append(customer_address)

    post_data = {
        'customer': customer_data
    }
    r = api('customers.json', post_data, 'POST')

    if isinstance(r,dict):
        if r.get('customer'):
            if r['customer'].get('id'):
                return r['customer'].get('id')
        else:
            print('Error: ' + str(r))
            return False
    else:
        print('Error: ' + str(r))
        return False
    


def order_import(order,order_ext,convert):
    post_data = {
        'order': {
            'financial_status': bc.get_order_status_target(convert['status']),
            'fulfillment_status': bc.get_order_status_target_shopify(convert['status']),
            'confirmed': True,
            'total_price': convert['total']['amount'],
            'subtotal_price': convert['subtotal']['amount'],
            'currency': convert['currency'],
            'processed_at': convert['created_at'],
            'updated_at': convert['updated_at'],
            'send_receipt': False,
            'send_fulfillment_receipt': False,
            'suppress_notifications': True,
            'customer': dict(),
            'billing_data': dict(),
            'shipping_data': dict(),
            'line_items': list()
        }
    }

    if convert['shipping']['amount']:
        post_data['order']['shipping_lines'] = list()
        ship_lines = dict()
        ship_lines['price'] = convert['shipping']['amount']
        ship_lines['title'] = convert['shipping']['title'] if convert['shipping']['title'] else 'Shipping'
        ship_lines['code'] = 'Shipping'
        post_data['order']['shipping_lines'].append(ship_lines)
    
    if convert['discount']['amount']:
        post_data['order']['discount_codes'] = list()
        discount_code = dict()
        post_data['order']['total_discounts'] = convert['discount']['amount']
        discount_code_title = 'Discount'
        if convert['discount']['code']:
            discount_code_title = convert['discount']['code']
        elif convert['discount']['title']:
            discount_code_title = convert['discount']['title']
        discount_code['code'] = discount_code_title
        discount_code['amount'] = convert['discount']['amount']
        discount_code['type'] = ''
        post_data['order']['discount_codes'].append(discount_code)

    if convert['tax']['amount']:
        post_data['order']['total_tax'] = convert['tax']['amount']
        total_ex_tax = float(convert['total']['amount']) - float(convert['tax']['amount'])
        rate = 0
        if total_ex_tax > 0:
            rate = round(float(convert['tax']['amount'])/total_ex_tax, 2)
        elif convert['total']['amount'] > 0:
            rate = round(float(convert['tax']['amount']) / convert['total']['amount'], 2)
        post_data['order']['tax_lines'] = [{
            'rate': rate,
            'title': 'TAX',
            'price': convert['tax']['amount']
        }]

    customer_id = False
    if convert['customer'] and convert['customer']['id']:
        customer_id = bc.get_map_field_by_src('customer', convert['customer']['id'])
    if customer_id:
        post_data['order']['customer']['id'] = customer_id
    else:
        post_data['order']['customer'] = {
            'first_name': convert['customer']['first_name'],
            'last_name': convert['customer']['last_name'],
            'email': convert['customer']['email'],
            'total_spent': convert['total']['amount']
        }
    
    for item in convert['items']:
        product_id = bc.get_map_field_by_src('product', item['product']['id'])
        variant_id = bc.get_map_field_by_src('product', item['product']['id'], 'value')
        if variant_id:
            item_data = {
                'variant_id': variant_id,
                'title': item['product']['name'],
                'price': item['price'],
                'quantity': int(item['qty']) if int(item['qty']) > 0 else 1,
                'sku': item['product']['sku'],
                'product_id': product_id if product_id else None,
                'total_discount': item['discount_amount'],
                'variant_title': None,
                'name': item['product']['name'],
                'properties': list(),
            }
            post_data['order']['line_items'].append(item_data)
        else:
            item_data = {
                'variant_id': None,
				'title': 'Product Name',
				'price': convert['total']['amount'],
				'quantity': 1,
				'sku': 'product-name',
				'product_id': None,
				'total_discount': '0.00',
				'variant_title': None,
				'name': 'Product Name',
				'properties': [],
            }
            post_data['order']['line_items'].append(item_data)
    r = api('orders.json', post_data, 'POST')
    if isinstance(r,dict):
        if r.get('order'):
            if r['order'].get('id'):
                return r['order'].get('id')
        else:
            print('Error: ' + str(r))
            return False
    else:
        print('Error: ' + str(r))
        return False
    
        


def clear_product():
    all_products = api('products.json?limit=100')
    print('\nClearing target products...')
    while all_products['products']:
        for product in all_products['products']:
            api('products/'+str(product['id'])+'.json',None,'DELETE')
        all_products = api('products.json?limit=100')
    return None

def clear_category():
    all_categories = api('custom_collections.json?limit=100')
    print('\nClearing target categories...')
    while all_categories['custom_collections']:
        for category in all_categories['custom_collections']:
            api('custom_collections/'+str(category['id'])+'.json',None,'DELETE')
        all_categories = api('custom_collections.json?limit=100')
    return None



def clear_customer():
    all_customers = api('customers.json?since_id=0&limit=100')
    print('\nClearing target customers...')
    while all_customers['customers']:
        for customer in all_customers['customers']:
            r = api('customers/'+str(customer['id'])+'.json',None,'DELETE')
        all_customers = api('customers.json?limit=100')
    return None

def clear_order():
    all_orders = api('orders.json?limit=100')
    print('\nClearing target orders...')
    while all_orders['orders']:
        for order in all_orders['orders']:
            api('orders/'+str(order['id'])+'.json',None,'DELETE')
        all_orders = api('orders.json?limit=100')
    return None

# if __name__ == '__main__':

