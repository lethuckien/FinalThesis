from unicodedata import decimal
import basecart as bc
import configparser
import shopify as shop

config = configparser.ConfigParser()
config.read('config.ini')
url_src = config.get('source', 'src_url').strip('/')






def get_count():
    queries = {
        'categories': "SELECT COUNT(*) FROM wp_term_taxonomy WHERE taxonomy = 'product_cat' ",
        'products': "SELECT COUNT(*) FROM wp_posts WHERE post_type = 'product'",
        'customers': "SELECT COUNT(*) FROM wp_users AS u LEFT JOIN wp_usermeta AS um ON u.ID = um.user_id WHERE (um.meta_key LIKE 'wp_capabilities' AND um.meta_value LIKE '%customer%' OR um.meta_value LIKE '%subscriber%')",
        'orders': "SELECT COUNT(*) FROM wp_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft')"
    }
    data = dict()
    for query in queries:
        data[query] = bc.query_connector(queries[query], 'count')
    return data



def get_product_main(id_src):
    query = "SELECT * FROM wp_posts WHERE ID > " + str(id_src) + " AND `post_type` LIKE 'product' LIMIT 1"
    return bc.query_connector(query)[0]

def get_product_ext(product_id):
    product_ext = dict()
    
    queries = {
        'product_variations': "SELECT * FROM wp_posts WHERE post_type = 'product_variation' AND post_parent = " + str(product_id),
        'term_relationship': "SELECT * FROM wp_term_relationships AS tr LEFT JOIN wp_term_taxonomy AS tx ON tx.term_taxonomy_id = tr.term_taxonomy_id LEFT JOIN wp_terms AS t ON t.term_id = tx.term_id WHERE tr.object_id = " + str(product_id),
    }
    
    for query in queries:
        product_ext[query] = bc.query_connector(queries[query])

    
    taxonomy_names = [attribute['taxonomy'] for attribute in product_ext['term_relationship']]
    attribute_name = list()
    for attr_name in taxonomy_names:
        if attr_name[:3] == 'pa_':
            attribute_name.append(attr_name)
    attribute_name = list(dict.fromkeys(attribute_name))
    attribute_name_query = ', '.join("'"+item[3:]+"'" for item in attribute_name)
    children_ids = [child['ID'] for child in product_ext['product_variations']]
    
    all_ids = children_ids
    all_ids.append(str(product_id))

    

    queries2 = {
        'postmeta': "SELECT * FROM wp_postmeta WHERE post_id IN (" + ', '.join(all_ids) + ')',
        'woocommerce_attribute_taxonomies': "SELECT * FROM wp_woocommerce_attribute_taxonomies WHERE attribute_name IN (" + attribute_name_query + ')',
        'variation_term_relationship': "SELECT * FROM wp_term_relationships AS tr LEFT JOIN wp_term_taxonomy AS tx ON tx.term_taxonomy_id = tr.term_taxonomy_id LEFT JOIN wp_terms AS t ON t.term_id = tx.term_id WHERE tr.object_id IN (" + ', '.join(children_ids) + ')'
    }
    for query in queries2:
        product_ext[query] = bc.query_connector(queries2[query])
    
    thumnail_list = list()
    gallery_list = ''

    for item in product_ext['postmeta']:
        if item['meta_key'] == '_thumbnail_id':
            thumb_data = {'product_id': item['post_id'], 'thumbnail_id': item['meta_value']}
            thumnail_list.append(thumb_data)
        elif item['meta_key'] == '_product_image_gallery':
            gallery_list = item['meta_value']
    thumbnail_id_list = [thumb['thumbnail_id'] for thumb in thumnail_list]
    queries3 = {
        'thumbnails': "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM wp_posts as p LEFT JOIN wp_postmeta as pm ON p.ID = pm.post_id AND pm.meta_key = '_wp_attached_file' WHERE p.ID IN ("+ ', '.join(thumbnail_id_list)+")",
        'gallery': "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM wp_posts as p LEFT JOIN wp_postmeta as pm ON p.ID = pm.post_id AND pm.meta_key = '_wp_attached_file' WHERE p.ID IN (" + gallery_list + ")"
    }
    if not gallery_list:
        del queries3['gallery']
    for query in queries3:
        product_ext[query] = bc.query_connector(queries3[query])
    product_ext['thumb_relationship'] = thumnail_list
    return product_ext
    
def convert_product(product, product_ext):
    product_data = bc.construct_product()
    product_data['id'] = product['ID']
    for thumb_data in product_ext['thumb_relationship']:
        if thumb_data['product_id'] == product_data['id']:
            thumb_id = thumb_data['thumbnail_id']
            for thumb in product_ext['thumbnails']:
                if thumb['ID'] == thumb_id:
                    url = thumb['guid']
                    url = url.replace('http://192.161.179.104/wordpress', url_src)
                    url = url.replace('http://localhost/wordpress', url_src)
                    product_data['thumb_image']['url'] = url
                    break
    if product_ext.get('gallery'):
        for gallery in product_ext['gallery']:
            url = gallery['guid']
            url = url.replace('http://192.161.179.104/wordpress', url_src)
            url = url.replace('http://localhost/wordpress', url_src)
            gallery_data = {
                'label': '',
                'url': gallery['guid'],
                'status': True,
            }
            product_data['images'].append(gallery_data)
    
    product_data['name'] = product['post_title']

    for meta in product_ext['postmeta']:
        if meta['post_id'] == product_data['id']:
            if meta['meta_key'] == '_sku':
                product_data['sku'] = meta['meta_value']
            if meta['meta_key'] == '_price':
                product_data['price'] = meta['meta_value']
            if meta['meta_key'] == '_sale_price':
                product_data['special_price']['price'] = meta['meta_value']
            if meta['meta_key'] == '_manage_stock':
                product_data['manage_stock'] = False if meta['meta_value'] == 'no' else True
            if meta['meta_key'] == '_stock':
                product_data['qty'] = meta['meta_value']
            if meta['meta_key'] == '_stock_status':
                product_data['is_in_stock'] = True if meta['meta_value'] == 'instock' else False
    
    product_data['description'] = product['post_content']
    product_data['short_description'] = product['post_excerpt']
    product_data['created_at'] = product['post_date']
    product_data['updated_at'] = product['post_modified']

    for term in product_ext['term_relationship']:
        if term['object_id'] == product_data['id']:
            if term['taxonomy'] == 'product_cat':
                product_data['categories'].append(term['term_id'])

    product_data['status'] = True if product['post_status'] == 'publish' else False

    for child in product_ext['product_variations']:
        child_data = bc.construct_product()
        child_data['id'] = child['ID']
        child_data['is_child'] = True
        child_attr_list = list()
        attr_value_list = list()
        for meta in product_ext['postmeta']:
            if meta['post_id'] == child_data['id']:
                if meta['meta_key'] == '_sku':
                    child_data['sku'] = meta['meta_value']
                if meta['meta_key'] == '_price':
                    child_data['price'] = meta['meta_value']
                if meta['meta_key'] == '_manage_stock':
                    child_data['manage_stock'] = False if meta['meta_value'] == 'no' else True
                if meta['meta_key'] == '_stock_status':
                    child_data['is_in_stock'] = True if meta['meta_value'] == 'instock' else False
                if meta['meta_key'] == '_stock':
                    child_data['qty'] = meta['meta_value']
                if meta['meta_key'] == '_variation_description':
                    child_data['description'] = meta['meta_value']
                if meta['meta_key'] == '_sale_price':
                    child_data['special_price']['price'] = meta['meta_value']
                if meta['meta_key'][:10] == 'attribute_':
                    attr_value_map = {
                        meta['meta_key'][13:]: meta['meta_value']
                    }
                    attr_value_list.append(meta['meta_key'][:10])
                    child_attr_list.append(attr_value_map)
        for child_attr in child_attr_list:
            for term in product_ext['term_relationship']:
                if child_attr[next(iter(child_attr))] == term['slug']:
                    child_attr[next(iter(child_attr))] = term['name']

        child_data['status'] = True if child['post_status'] == 'publish' else False
        child_data['created_at'] = child['post_date']
        child_data['updated_at'] = child['post_modified']
        child_data['name'] = child['post_title']
        
        for thumb_data in product_ext['thumb_relationship']:
            if thumb_data['product_id'] == child_data['id']:
                thumb_id = thumb_data['thumbnail_id']
                for thumb in product_ext['thumbnails']:
                    if thumb['ID'] == thumb_id:
                        url = thumb['guid']
                        url = url.replace('http://192.161.179.104/wordpress', url_src)
                        url = url.replace('http://localhost/wordpress', url_src)
                        child_data['thumb_image']['url'] = url
                        break
        for attr in child_attr_list:
            attr_data = dict()
            attr_data['all_values'] = list()
            attr_code = 'pa_'+str(next(iter(attr)))
            for term in product_ext['term_relationship']:
                if term['taxonomy'] == attr_code:
                    attr_data['all_values'].append(term['name'])
            for woo_attr in product_ext['woocommerce_attribute_taxonomies']:
                if woo_attr['attribute_name'] == next(iter(attr)):
                    attr_data['attribute_id'] = woo_attr['attribute_id']
                    attr_data['attribute_name'] = woo_attr['attribute_label']
                    attr_data['attribute_type'] = woo_attr['attribute_type']
                    attr_data['attribute_value'] = attr[next(iter(attr))]
                    child_data['attributes'].append(attr_data)
        product_data['children'].append(child_data)
    return product_data





def get_category_main(id_src):
    query = "SELECT * FROM wp_term_taxonomy as tx LEFT JOIN wp_terms AS t ON t.term_id = tx.term_id WHERE tx.taxonomy = 'product_cat' AND tx.term_id > " + str(id_src) + " AND t.term_id IS NOT NULL ORDER BY tx.term_id ASC LIMIT 1"
    return bc.query_connector(query)[0]

def get_category_ext(category_id):
    category_ext = dict()
    
    queries = {
        'termmeta': "SELECT * FROM wp_termmeta WHERE term_id = " + str(category_id) + " AND meta_key = 'thumbnail_id'"
    }

    for query in queries:
        category_ext[query] = bc.query_connector(queries[query])

    thumbnail_ids = [meta['meta_value'] for meta in category_ext['termmeta']]
    thumbnail_query = "SELECT p.ID, p.post_title, pm.meta_value, p.guid FROM wp_posts AS p LEFT JOIN wp_postmeta AS pm ON pm.post_id = p.ID AND pm.meta_key = '_wp_attached_file' WHERE p.ID IN (" + ', '.join(thumbnail_ids)+ ')'
    category_ext['postmeta'] = bc.query_connector(thumbnail_query)[0]
    return category_ext

def convert_category(category, category_ext):
    category_data = bc.construct_category()
    category_data['id'] = category['term_id']
    img_url = category_ext['postmeta']['guid']
    img_url = img_url.replace('http://192.161.179.104/wordpress', url_src)
    img_url = img_url.replace('http://localhost/wordpress', url_src)
    category_data['thumb_image']['url'] = img_url
    category_data['name'] = category['name']
    category_data['description'] = category['description']
    return category_data


def get_customer_main(id_src):
    query = "SELECT * FROM wp_users AS u LEFT JOIN wp_usermeta AS um ON u.ID = um.user_id WHERE (um.meta_key LIKE 'wp_capabilities' AND um.meta_value LIKE '%customer%' OR um.meta_value LIKE '%subscriber%') AND ID > "+str(id_src)+" ORDER BY ID ASC LIMIT 1"
    return bc.query_connector(query)[0]

def get_customer_ext(customer_id):
    query = "SELECT * FROM wp_usermeta WHERE user_id = " + str(customer_id)
    return bc.query_connector(query)

def convert_customer(customer, customer_ext):
    customer_data = bc.construct_customer()
    customer_data['id'] = customer['ID']
    customer_data['username'] = customer['user_login']
    customer_data['email'] = customer['user_email']
    customer_data['password'] = customer['user_pass']

    billing_address = bc.construct_customer_address()
    billing_address['billing'] = True
    shipping_address = bc.construct_customer_address()
    shipping_address['shipping'] = True
    for meta in customer_ext:
        if meta['meta_key'] == 'first_name':
            customer_data['first_name'] = meta['meta_value']
        if meta['meta_key'] == 'last_name':
            customer_data['last_name'] = meta['meta_value']
        if meta['meta_key'] == 'wp_capabilities':
            customer_data['is_subscribed'] = True if meta['meta_value'] == 'subscriber' else False
        if meta['meta_key'].startswith('billing_'):
            if meta['meta_key'] == 'billing_address_1':
                billing_address['address_1'] = meta['meta_value']
            if meta['meta_key'] == 'billing_address_2':
                billing_address['address_2'] = meta['meta_value']
            if meta['meta_key'] == 'billing_city':
                billing_address['city'] = meta['meta_value']
            if meta['meta_key'] == 'billing_postcode':
                billing_address['postcode'] = meta['meta_value']
            if meta['meta_key'] == 'billing_telephone':
                billing_address['phone'] = meta['meta_value']
            if meta['meta_key'] == 'billing_company':
                billing_address['company'] = meta['meta_value']
            if meta['meta_key'] == 'billing_fax':
                billing_address['fax'] = meta['meta_value']
            if meta['meta_key'] == 'billing_country':
                billing_address['country'] = meta['meta_value']
            if meta['meta_key'] == 'billing_state':
                billing_address['state'] = meta['meta_value']
        if meta['meta_key'].startswith('shipping_'):
            if meta['meta_key'] == 'shipping_address_1':
                shipping_address['address_1'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_address_2':
                shipping_address['address_2'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_city':
                shipping_address['city'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_postcode':
                shipping_address['postcode'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_telephone':
                shipping_address['phone'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_company':
                shipping_address['company'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_fax':
                shipping_address['fax'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_country':
                shipping_address['country'] = meta['meta_value']
            if meta['meta_key'] == 'shipping_state':
                shipping_address['state'] = meta['meta_value']
    customer_data['address'].append(billing_address)
    customer_data['address'].append(shipping_address)
    
    customer_data['created_at'] = customer['user_registered']
    
    return customer_data


def get_order_main(id_src):
    query = "SELECT * FROM wp_posts WHERE post_type = 'shop_order' AND post_status NOT IN ('inherit','auto-draft') AND ID > " + str(id_src) + " ORDER BY ID ASC LIMIT 1"
    return bc.query_connector(query)[0]

def get_order_ext(order_id):
    order_ext = dict()
    queries = {
        'order_items': "SELECT * FROM wp_woocommerce_order_items WHERE order_id = "+str(order_id),
        'order_note': "SELECT * FROM wp_comments WHERE comment_post_ID = " +str(order_id),
        'order_meta': "SELECT * FROM wp_postmeta WHERE post_id = " + str(order_id),
    }

    for query in queries:
        order_ext[query] = bc.query_connector(queries[query])
    

    order_item_ids = [item['order_item_id'] for item in order_ext['order_items']]
    customer_ids = list()
    for meta in order_ext['order_meta']:
        if meta['meta_key'] == '_customer_user':
            customer_ids.append(meta['meta_value'])

    queries2 = {
        'order_item_meta': "SELECT * FROM wp_woocommerce_order_itemmeta WHERE order_item_id IN (" + ','.join(order_item_ids) + ")",
        'user': "SELECT * FROM wp_users WHERE ID IN (" + ','.join(customer_ids)+ ")",
        'user_meta': "SELECT * FROM wp_usermeta WHERE user_id IN (" + ','.join(customer_ids)+ ") AND meta_key IN ('first_name','last_name')"
    }
    for query in queries2:
        order_ext[query] = bc.query_connector(queries2[query])

    item_list = list()
    for meta in order_ext['order_item_meta']:
        if meta['meta_key'] == '_product_id':
            item_list.append(meta['meta_value'])

    query3 = "SELECT * FROM wp_postmeta WHERE post_id IN (" + ','.join(item_list)+")"
    order_ext['product_meta'] = bc.query_connector(query3)
    return order_ext


def convert_order(order, order_ext):
    order_data = bc.construct_order()
    order_data['id'] = order['ID']
    order_data['status'] = order['post_status']
    order_data['created_at'] = order['post_date']
    order_data['updated_at'] = order['post_modified']
    billing_address = bc.construct_order_address()
    shipping_address = bc.construct_order_address()
    for meta in order_ext['order_meta']:
        if meta['meta_key'] == '_order_number':
            order_data['order_id'] = meta['meta_value']
        if meta['meta_key'] == '_order_total':
            order_data['total']['amount'] = meta['meta_value']
        if meta['meta_key'] == '_order_shipping':
            order_data['shipping']['amount'] = meta['meta_value']
        if meta['meta_key'] == '_order_currency':
            order_data['currency'] = meta['meta_value']
        if meta['meta_key'] == '_cart_discount':
            order_data['discount']['amount'] = meta['meta_value']
        if meta['meta_key'] == '_order_tax':
            order_data['tax']['amount'] = meta['meta_value']
        
        if meta['meta_key'] == '_billing_first_name':
            billing_address['first_name'] = meta['meta_value']
        if meta['meta_key'] == '_billing_last_name':
            billing_address['last_name'] = meta['meta_value']
        if meta['meta_key'] == '_billing_email':
            billing_address['email'] = meta['meta_value']
        if meta['meta_key'] == '_billing_address_1':
            billing_address['address_1'] = meta['meta_value']
        if meta['meta_key'] == '_billing_address_2':
            billing_address['address_2'] = meta['meta_value']
        if meta['meta_key'] == '_billing_city':
            billing_address['city'] = meta['meta_value']
        if meta['meta_key'] == '_billing_postcode':
            billing_address['postcode'] = meta['meta_value']
        if meta['meta_key'] == '_billing_phone':
            billing_address['telephone'] = meta['meta_value']
        if meta['meta_key'] == '_billing_company':
            billing_address['company'] = meta['meta_value']
        if meta['meta_key'] == '_billing_country':
            billing_address['country'] = meta['meta_value']
        if meta['meta_key'] == '_billing_state':
            billing_address['state'] = meta['meta_value']

        if meta['meta_key'] == '_shipping_first_name':
            shipping_address['first_name'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_last_name':
            shipping_address['last_name'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_email':
            shipping_address['email'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_address_1':
            shipping_address['address_1'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_address_2':
            shipping_address['address_2'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_city':
            shipping_address['city'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_postcode':
            shipping_address['postcode'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_phone':
            shipping_address['telephone'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_company':
            shipping_address['company'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_country':
            shipping_address['country'] = meta['meta_value']
        if meta['meta_key'] == '_shipping_state':
            shipping_address['state'] = meta['meta_value']
    
    order_data['billing_address'] = billing_address
    order_data['shipping_address'] = shipping_address
    order_data['customer_address'] = billing_address

    order_data['subtotal']['amount'] = float(order_data['total']['amount']) - float(order_data['discount']['amount']) if order_data['total']['amount'] and order_data['discount']['amount'] else 0
    for product in order_ext['order_items']:
        item_data = bc.construct_order_item()
        item_data['id'] = product['order_item_id']
        item_data['product']['name'] = product['order_item_name']
        for meta in order_ext['order_item_meta']:
            if meta['order_item_id'] == product['order_item_id']:
                if meta['meta_key'] == '_product_id':
                    item_data['product']['id'] = meta['meta_value']
                if meta['meta_key'] == '_variation_id':
                    item_data['product']['var_id'] = meta['meta_value']
                if meta['meta_key'] == '_qty':
                    item_data['qty'] = meta['meta_value']
                if meta['meta_key'] == '_line_subtotal':
                    item_data['subtotal'] = meta['meta_value']
                if meta['meta_key'] == '_line_tax':
                    item_data['tax_ammount'] = meta['meta_value']

        try:
            item_data['price'] = float(item_data['subtotal']) / float(item_data['qty'])
        except:
            item_data['price'] = 0
        search_id = 0
        if int(item_data['product']['var_id']) != 0:
            search_id = item_data['product']['var_id']
        else: 
            search_id = item_data['product']['id']
        for meta in order_ext['product_meta']:
            if meta['post_id'] == search_id:
                if meta['meta_key'] == '_sku':
                    item_data['product']['sku'] = meta['meta_value']
        order_data['items'].append(item_data)

        customer_data = bc.construct_order_customer()
        customer_data['id'] = order_ext['user'][0]['ID']
        customer_data['email'] = order_ext['user'][0]['user_email']
        customer_data['username'] = order_ext['user'][0]['user_login']
        for meta in order_ext['user_meta']:
            if meta['meta_key'] == 'first_name':
                customer_data['first_name'] = meta['meta_value']
            if meta['meta_key'] == 'last_name':
                customer_data['last_name'] = meta['meta_value']
        
        order_data['customer'] = customer_data
    return order_data



    
if __name__ == '__main__':
    # print(get_count())
    main = get_product_main(34)
    ext = get_product_ext(int(main['ID']))
    # # print(ext)
    convert = convert_product(main,ext)
    print(convert)
    # shop.order_import(0,0,convert)
    