import basecart as bc
import configparser
import mysql.connector as sql
import map
from tqdm import tqdm




def insert_map(id_src=None, id_dest=None, additional_data=None, value=None, type=None):
    conn = map.get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO migration_map (id_src,id_dest,additional_data,value,type, migration_id) VALUES (%s,%s,%s,%s,%s,%s)", [id_src,id_dest,additional_data,value,type, migration_id])
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == '__main__':
    migration_id = map.new_map()
    entity_clear_order = ('category','product','order','customer')

    config = configparser.ConfigParser()
    config.read('config.ini')

    src_type = config.get('source', 'src_type')
    exec('import '+ src_type + ' as src')

    tar_type = config.get('target', 'tar_type')
    exec('import '+ tar_type + ' as tar')

    print('Starting migration ID ' + str(migration_id))

    count = src.get_count()

    if config.getboolean('clear', 'category'):
        tar.clear_category()
    if config.getboolean('clear', 'product'):
        tar.clear_product()
    if config.getboolean('clear', 'order'):
        tar.clear_order()
    if config.getboolean('clear', 'customer'):
        tar.clear_customer()
    
    
    if config.getboolean('config', 'category'):    
        id_src = 0
        print('\nMigrating categories \n')
        for loop in tqdm(range(count['categories'])):
            category = src.get_category_main(id_src)
            category_id = int(category['term_id'])
            category_ext = src.get_category_ext(category_id)
            convert = src.convert_category(category, category_ext)
            id_dest = tar.category_import(category,category_ext,convert)
            if id_dest:
                insert_map(category_id, id_dest, type='category')
            id_src = category_id

    if config.getboolean('config', 'product'):
        id_src = 0
        print('\nMigrating products \n')
        for loop in tqdm(range(count['products'])):
            product = src.get_product_main(id_src)
            product_id = int(product['ID'])
            product_ext = src.get_product_ext(product_id)
            convert = src.convert_product(product, product_ext)
            id_dest, id_variant = tar.product_import(product,product_ext, convert)
            if id_dest and id_variant:
                insert_map(product_id, id_dest,value = id_variant, type='product')
            id_src = product_id

    if config.getboolean('config', 'customer'):
        print('\nMigrating customers \n')
        id_src = 0
        for loop in tqdm(range(count['customers'])):
            customer = src.get_customer_main(id_src)
            customer_id = int(customer['ID'])
            customer_ext = src.get_customer_ext(customer_id)
            convert = src.convert_customer(customer, customer_ext)
            id_dest = tar.customer_import(customer,customer_ext, convert)
            if id_dest:
                insert_map(customer_id, id_dest, type='customer')
            # print(id_dest)
            id_src = customer_id

    if config.getboolean('config', 'order'):
        print('\nMigrating orders \n')
        id_src = 0
        for loop in tqdm(range(count['orders'])):
            order = src.get_order_main(id_src)
            order_id = int(order['ID'])
            order_ext = src.get_order_ext(order_id)
            convert = src.convert_order(order, order_ext)
            id_dest = tar.order_import(order,order_ext, convert)
            if id_dest:
                insert_map(order_id, id_dest, type='order')
            # print(id_dest)
            id_src = order_id


    print('\nMigration Completed\nCheck results here: ' + config.get('target', 'tar_url'))








