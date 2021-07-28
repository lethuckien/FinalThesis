import mysql.connector as sql

host = 'localhost'
user = 'root'
password = '1'
migration_id = 0


def new_map():
    with open('mig_count.txt','r+') as f:
        migration_id = int(f.read()) + 1
    with open('mig_count.txt', 'w') as f:    
        f.write(str(migration_id))


    conn = sql.connect(host=host, user=user,password=password)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE migration_"+str(migration_id)) 
    cursor.execute("USE migration_"+str(migration_id))

    cursor.execute("CREATE TABLE `migration_map` (`id` bigint  AUTO_INCREMENT PRIMARY KEY,`migration_id` int ,`type` varchar(255) ,`id_src` bigint ,`id_dest` bigint ,`additional_data` varchar(255) ,`value` varchar(255) );")
    cursor.close()
    conn.close()
    return migration_id

def get_conn():
    with open('mig_count.txt','r+') as f:
        migration_id = int(f.read())
    conn = sql.connect(host=host, user=user,password=password, database='migration_'+str(migration_id))

    return conn

