# coding:utf-8

import sys
import io
import os
import time
import re
import json
import datetime
import yaml

sys.path.append(os.getcwd() + "/class/core")
import mw

app_debug = False
if mw.isAppleSystem():
    app_debug = True


# /usr/lib/systemd/system/mongod.service
# /var/lib/mongo

def getPluginName():
    return 'mongodb'


def getPluginDir():
    return mw.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return mw.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getConf():
    path = getServerDir() + "/mongodb.conf"
    return path


def getConfTpl():
    path = getPluginDir() + "/config/mongodb.conf"
    return path

def getConfigData():
    cfg = getConf()
    config_data = mw.readFile(cfg)
    try:
        config = yaml.safe_load(config_data)
    except:
        config = {
            "systemLog": {
                "destination": "file",
                "logAppend": True,
                "path": mw.getServerDir()+"/mongodb/log/mongodb.log"
            },
            "storage": {
                "dbPath": mw.getServerDir()+"/mongodb/data",
                "directoryPerDB": True,
                "journal": {
                    "enabled": True
                }
            },
            "processManagement": {
                "fork": True,
                "pidFilePath": mw.getServerDir()+"/mongodb/log/mongodb.pid"
            },
            "net": {
                "port": 27017,
                "bindIp": "0.0.0.0"
            },
            "security": {
                "authorization": "enabled",
                "javascriptEnabled": False
            }
        }
    return config

def setConfig(config_data):
    t = status()


    cfg = getConf()
    try:
        mw.writeFile(cfg, yaml.safe_dump(config_data))
    except:
        return False
    return True

def getInitDTpl():
    path = getPluginDir() + "/init.d/" + getPluginName() + ".tpl"
    return path


def getConfPort():
    data = getConfigData()
    return data['net']['port']
    # file = getConf()
    # content = mw.readFile(file)
    # rep = 'port\s*=\s*(.*)'
    # tmp = re.search(rep, content)
    # return tmp.groups()[0].strip()

def getConfAuth():
    data = getConfigData()
    return data['security']['authorization']
    # file = getConf()
    # content = mw.readFile(file)
    # rep = 'auth\s*=\s*(.*)'
    # tmp = re.search(rep, content)
    # return tmp.groups()[0].strip()

def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':', 1)
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':', 1)
            tmp[t[0]] = t[1]

    return tmp

def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, mw.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, mw.returnJson(True, 'ok'))

def status():
    data = mw.execShell(
        "ps -ef|grep mongod |grep -v mongosh|grep -v grep | grep -v /Applications | grep -v python | grep -v mdserver-web | awk '{print $2}'")
    if data[0] == '':
        return 'stop'
    return 'start'

def pSqliteDb(dbname='users'):
    file = getServerDir() + '/mongodb.db'
    name = 'mongodb'

    sql_file = getPluginDir() + '/config/mongodb.sql'
    import_sql = mw.readFile(sql_file)
    # print(sql_file,import_sql)
    md5_sql = mw.md5(import_sql)

    import_sign = False
    save_md5_file = getServerDir() + '/import_mongodb.md5'
    if os.path.exists(save_md5_file):
        save_md5_sql = mw.readFile(save_md5_file)
        if save_md5_sql != md5_sql:
            import_sign = True
            mw.writeFile(save_md5_file, md5_sql)
    else:
        mw.writeFile(save_md5_file, md5_sql)

    if not os.path.exists(file) or import_sql:
        conn = mw.M(dbname).dbPos(getServerDir(), name)
        csql_list = import_sql.split(';')
        for index in range(len(csql_list)):
            conn.execute(csql_list[index], ())

    conn = mw.M(dbname).dbPos(getServerDir(), name)
    return conn

def mongdbClientS():
    import pymongo
    port = getConfPort()
    auth = getConfAuth()
    mg_root = pSqliteDb('config').where('id=?', (1,)).getField('mg_root')

    if auth == 'disabled':
        client = pymongo.MongoClient(host='127.0.0.1', port=int(port), directConnection=True)
    else:
        # print(auth,mg_root)
        client = pymongo.MongoClient(host='127.0.0.1', port=int(port), directConnection=True, username='root',password=mg_root)
    return client

def mongdbClient():
    import pymongo
    port = getConfPort()
    auth = getConfAuth()
    mg_root = pSqliteDb('config').where('id=?', (1,)).getField('mg_root')

    
    if auth == 'disabled':
        client = pymongo.MongoClient(host='127.0.0.1', port=int(port), directConnection=True)
    else:
        # print(auth,mg_root)
        # uri = "mongodb://root:"+mg_root+"@127.0.0.1:"+str(port)
        # client = pymongo.MongoClient(uri)
        client = pymongo.MongoClient(host='127.0.0.1', port=int(port), directConnection=True, username='root',password=mg_root)
    return client


def initDreplace():

    file_tpl = getInitDTpl()
    service_path = os.path.dirname(os.getcwd())

    initD_path = getServerDir() + '/init.d'
    if not os.path.exists(initD_path):
        os.mkdir(initD_path)
    file_bin = initD_path + '/' + getPluginName()

    logs_dir = getServerDir() + '/logs'
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    data_dir = getServerDir() + '/data'
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    install_ok = getServerDir() + "/install.lock"
    if os.path.exists(install_ok):
        return file_bin
    mw.writeFile(install_ok, 'ok')

    # initd replace
    content = mw.readFile(file_tpl)
    content = content.replace('{$SERVER_PATH}', service_path)
    mw.writeFile(file_bin, content)
    mw.execShell('chmod +x ' + file_bin)

    # config replace
    conf_content = mw.readFile(getConfTpl())
    conf_content = conf_content.replace('{$SERVER_PATH}', service_path)
    mw.writeFile(getServerDir() + '/mongodb.conf', conf_content)

    # systemd
    systemDir = mw.systemdCfgDir()
    systemService = systemDir + '/mongodb.service'
    systemServiceTpl = getPluginDir() + '/init.d/mongodb.service.tpl'
    if os.path.exists(systemDir) and not os.path.exists(systemService):
        service_path = mw.getServerDir()
        se_content = mw.readFile(systemServiceTpl)
        se_content = se_content.replace('{$SERVER_PATH}', service_path)
        mw.writeFile(systemService, se_content)
        mw.execShell('systemctl daemon-reload')

    return file_bin


def mgOp(method):
    file = initDreplace()
    if mw.isAppleSystem():
        data = mw.execShell(file + ' ' + method)
        # print(data)
        if data[1] == '':
            return 'ok'
        return data[1]

    data = mw.execShell('systemctl ' + method + ' ' + getPluginName())
    if data[1] == '':
        return 'ok'
    return 'fail'


def start():
    mw.execShell(
        'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/www/server/lib/openssl11/lib')
    return mgOp('start')


def stop():
    return mgOp('stop')


def reload():
    return mgOp('reload')


def restart():
    if os.path.exists("/tmp/mongodb-27017.sock"):
        mw.execShell('rm -rf ' + "/tmp/mongodb-27017.sock")

    return mgOp('restart')


def getConfig():
    t = status()
    if t == 'stop':
        return mw.returnJson(False,'未启动!')
    d = getConfigData()
    return mw.returnJson(True,'ok',d)

def saveConfig():
    d = getConfigData()
    args = getArgs()
    data = checkArgs(args, ['bind_ip','port','data_path','log','pid_file_path'])
    if not data[0]:
        return data[1]

    d['net']['bindIp'] = args['bind_ip']
    d['net']['port'] = int(args['port'])

    d['storage']['dbPath'] = args['data_path']
    d['systemLog']['path'] = args['log']
    d['processManagement']['pidFilePath'] = args['pid_file_path']
    setConfig(d)
    reload()
    return mw.returnJson(True,'设置成功')

def initMgRoot(password='',force=0):
    if force == 1:
        d = getConfigData()
        auth_t = d['security']['authorization']
        d['security']['authorization'] = 'disabled'
        setConfig(d)
        reload()

    client = mongdbClient()
    db = client.admin
    
    db_all_rules = [
        {'role': 'root', 'db': 'admin'},
        {'role': 'clusterAdmin', 'db': 'admin'},
        {'role': 'readAnyDatabase', 'db': 'admin'},
        {'role': 'readWriteAnyDatabase', 'db': 'admin'},
        {'role': 'userAdminAnyDatabase', 'db': 'admin'},
        {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
        {'role': 'userAdmin', 'db': 'admin'},
        {'role': 'dbAdmin', 'db': 'admin'}
    ]

    if password =='':
        mg_pass = mw.getRandomString(8)
    else:
        mg_pass = password

    try:
        db.command("createUser", "root", pwd=mg_pass, roles=db_all_rules)
    except Exception as e:
        if force == 0:
            db.command("updateUser", "root", pwd=mg_pass, roles=db_all_rules)
        else:
            db.command('dropUser','root')
            db.command("createUser", "root", pwd=mg_pass, roles=db_all_rules)
    r = pSqliteDb('config').where('id=?', (1,)).save('mg_root',(mg_pass,))

    if force == 1:
        d['security']['authorization'] = auth_t
        setConfig(d)
        reload()
    return True

def initUserRoot():
    d = getConfigData()
    auth_t = d['security']['authorization']
    d['security']['authorization'] = 'disabled'
    setConfig(d)
    reload()

    client = mongdbClient()
    db = client.admin
    
    db_all_rules = [
        {'role': 'root', 'db': 'admin'},
        {'role': 'clusterAdmin', 'db': 'admin'},
        {'role': 'readAnyDatabase', 'db': 'admin'},
        {'role': 'readWriteAnyDatabase', 'db': 'admin'},
        {'role': 'userAdminAnyDatabase', 'db': 'admin'},
        {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
        {'role': 'userAdmin', 'db': 'admin'},
        {'role': 'dbAdmin', 'db': 'admin'}
    ]
    # db.command("updateUser", "root", pwd=mg_pass, roles=db_all_rules)
    mg_pass = mw.getRandomString(8)
    try:
        r1 = db.command("createUser", "root", pwd=mg_pass, roles=db_all_rules)
        # print(r1)
    except Exception as e:
        # print(e)
        r1 = db.command('dropUser','root')
        r2 = db.command("createUser", "root", pwd=mg_pass, roles=db_all_rules)
        # print(r1, r2)
        
    r = pSqliteDb('config').where('id=?', (1,)).save('mg_root',(mg_pass,))

    d['security']['authorization'] = auth_t
    setConfig(d)
    reload()
    return True

def setConfigAuth():
    init_db_root = getServerDir() + '/init_db_root.lock'
    if not os.path.exists(init_db_root):
        initUserRoot()
        mw.writeFile(init_db_root,'ok')

    d = getConfigData()
    if d['security']['authorization'] == 'enabled':
        d['security']['authorization'] = 'disabled'
        setConfig(d)
        reload()
        return mw.returnJson(True,'关闭成功')
    else:
        d['security']['authorization'] = 'enabled'
        setConfig(d)
        reload()
        return mw.returnJson(True,'开启成功')

def runInfo():
    '''
    cd /www/server/mdserver-web && source bin/activate && python3 /www/server/mdserver-web/plugins/mongodb/index.py run_info
    '''
    client = mongdbClient()
    db = client.admin
    serverStatus = db.command('serverStatus')

    listDbs = client.list_database_names()

    result = {}
    result["host"] = serverStatus['host']
    result["version"] = serverStatus['version']
    result["uptime"] = serverStatus['uptime']
    result['db_path'] = getServerDir() + "/data"
    result["connections"] = serverStatus['connections']['current']
    result["collections"] = len(listDbs)

    pf = serverStatus['opcounters']
    result['pf'] = pf
    
    return mw.getJson(result)


def runDocInfo():    
    client = mongdbClient()
    db = client.admin
    # print(db)
    serverStatus = db.command('serverStatus')

    listDbs = client.list_database_names()
    showDbList = []
    result = {}
    for x in range(len(listDbs)):
        mongd = client[listDbs[x]]
        stats = mongd.command({"dbstats": 1})
        if 'operationTime' in stats:
            del stats['operationTime']

        if '$clusterTime' in stats:
            del stats['$clusterTime']
        showDbList.append(stats)

    result["dbs"] = showDbList
    return mw.getJson(result)

def runReplInfo():
    client = mongdbClient()
    db = client.admin
    serverStatus = db.command('serverStatus')

    result = {}
    result['status'] = '无'
    result['doc_name'] = '无'
    if 'repl' in serverStatus:
        repl = serverStatus['repl']
        # print(repl)
        result['status'] = '从'
        if 'ismaster' in repl and repl['ismaster']:
            result['status'] = '主'

        if 'secondary' in repl and not repl['secondary']:
            result['status'] = '主'

        result['setName'] = mw.getDefault(repl,'setName', '') 
        result['primary'] = mw.getDefault(repl,'primary', '') 
        result['me'] = mw.getDefault(repl,'me', '') 

        hosts = mw.getDefault(repl,'hosts', '') 
        result['hosts'] = ','.join(hosts)

    
    return mw.returnJson(True, 'OK', result)

def getDbList():
    args = getArgs()
    page = 1
    page_size = 10
    search = ''
    data = {}
    if 'page' in args:
        page = int(args['page'])

    if 'page_size' in args:
        page_size = int(args['page_size'])

    if 'search' in args:
        search = args['search']

    conn = pSqliteDb('databases')
    limit = str((page - 1) * page_size) + ',' + str(page_size)
    condition = ''
    if not search == '':
        condition = "name like '%" + search + "%'"
    field = 'id,name,username,password,accept,rw,ps,addtime'
    clist = conn.where(condition, ()).field(
        field).limit(limit).order('id desc').select()

    # for x in range(0, len(clist)):
    #     dbname = clist[x]['name']
    #     # blist = getDbBackupListFunc(dbname)
    #     # # print(blist)
    #     clist[x]['is_backup'] = False
    #     if len(blist) > 0:
    #         clist[x]['is_backup'] = True

    count = conn.where(condition, ()).count()
    _page = {}
    _page['count'] = count
    _page['p'] = page
    _page['row'] = page_size
    _page['tojs'] = 'dbList'
    data['page'] = mw.getPage(_page)
    data['data'] = clist

    info = {}
    info['root_pwd'] = pSqliteDb('config').where('id=?', (1,)).getField('mg_root')
    data['info'] = info
    return mw.getJson(data)
    # return mw.returnJson(True,'ok',data)

def addDb():
    t = status()
    if t == 'stop':
        return mw.returnJson(False,'未启动!')

    client = mongdbClient()
    db = client.admin

    args = getArgs()
    data = checkArgs(args, ['ps','name','db_user','password'])
    if not data[0]:
        return data[1]

    data_name = args['name'].strip()
    if not data_name:
        return mw.returnJson(False, "数据库名不能为空！")

    nameArr = ['admin', 'config', 'local']
    if data_name in nameArr:
        return mw.returnJson(False, "数据库名是保留名称!")

    addTime = time.strftime('%Y-%m-%d %X', time.localtime())
    username = ''
    password = ''
    # auth为true时如果__DB_USER为空则将它赋值为 root，用于开启本地认证后数据库用户为空的情况
    auth_status = getConfAuth() == "enabled"  
    
    if auth_status:
        data_name = args['name']
        username = args['db_user']
        password = args['password']
    else:
        username = data_name


    client[data_name].chat.insert_one({})
    user_roles = [{'role': 'dbOwner', 'db': data_name}, {'role': 'userAdmin', 'db': data_name}]
    if auth_status:
        # db.command("dropUser", username)
        db.command("createUser", username, pwd=password, roles=user_roles)

    ps = args['ps']
    if ps == '': 
        ps = data_name

    # 添加入SQLITE
    pSqliteDb('databases').add('name,username,password,accept,ps,addtime', (data_name, username, password, '127.0.0.1', ps, addTime))
    return mw.returnJson(True, '添加成功')


def delDb():
    client = mongdbClient()
    db = client.admin
    sqlite_db = pSqliteDb('databases')

    args = getArgs()
    data = checkArgs(args, ['id', 'name'])
    if not data[0]:
        return data[1]
    try:
        sid = args['id']
        name = args['name']
        find = sqlite_db.where("id=?", (sid,)).field('id,name,username,password,accept,ps,addtime').find()
        accept = find['accept']
        username = find['username']

        client.drop_database(name)

        try:
            db.command('dropUser',username)
        except Exception as e:
            pass

        # 删除SQLITE
        sqlite_db.where("id=?", (sid,)).delete()
        return mw.returnJson(True, '删除成功!')
    except Exception as ex:
        return mw.returnJson(False, '删除失败!' + str(ex))

def setRootPwd(version=''):
    args = getArgs()
    data = checkArgs(args, ['password'])
    if not data[0]:
        return data[1]

    #强制修改
    force = 0
    if 'force' in args and args['force'] == '1':
        force = 1

    password = args['password']
    try:
        msg = ''
        if force == 1:
            msg = ',无须强制!'
        initMgRoot(password, force)
        return mw.returnJson(True, '数据库root密码修改成功!'+msg)
    except Exception as ex:
        return mw.returnJson(False, '修改错误:' + str(ex))

def setUserPwd(version=''):

    client = mongdbClient()
    db = client.admin
    sqlite_db = pSqliteDb('databases')

    args = getArgs()
    data = checkArgs(args, ['password', 'name'])
    if not data[0]:
        return data[1]

    newpassword = args['password']
    username = args['name']
    uid = args['id']
    try:
        name = sqlite_db.where('id=?', (uid,)).getField('name')
        user_roles = [{'role': 'dbOwner', 'db': name}, {'role': 'userAdmin', 'db': name}]

        try:
            db.command("updateUser", username, pwd=newpassword, roles=user_roles)
        except Exception as e:
            db.command("createUser", username, pwd=newpassword, roles=user_roles)

        sqlite_db.where("id=?", (uid,)).setField('password', newpassword)
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]密码成功!', (name,)))
    except Exception as ex:
        return mw.returnJson(False, mw.getInfo('修改数据库[{1}]密码失败[{2}]!', (name, str(ex),)))


def syncGetDatabases():
    client = mongdbClient()
    sqlite_db = pSqliteDb('databases')
    db = client.admin
    data = client.admin.command({"listDatabases": 1})
    nameArr = ['admin', 'config', 'local']
    n = 0

    for value in data['databases']:
        vdb_name = value["name"]
        b = False
        for key in nameArr:
            if vdb_name == key:
                b = True
                break
        if b:
            continue
        if sqlite_db.where("name=?", (vdb_name,)).count() > 0:
            continue

        host = '127.0.0.1'
        ps = vdb_name
        addTime = time.strftime('%Y-%m-%d %X', time.localtime())
        if sqlite_db.add('name,username,password,accept,ps,addtime', (vdb_name, vdb_name, '', host, ps, addTime)):
            n += 1

    msg = mw.getInfo('本次共从服务器获取了{1}个数据库!', (str(n),))
    return mw.returnJson(True, msg)

def setDbPs():
    args = getArgs()
    data = checkArgs(args, ['id', 'name', 'ps'])
    if not data[0]:
        return data[1]

    ps = args['ps']
    sid = args['id']
    name = args['name']
    try:
        psdb = pSqliteDb('databases')
        psdb.where("id=?", (sid,)).setField('ps', ps)
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]备注成功!', (name,)))
    except Exception as e:
        return mw.returnJson(True, mw.getInfo('修改数据库[{1}]备注失败!', (name,)))


def getDbInfo():
    args = getArgs()
    data = checkArgs(args, ['name'])
    if not data[0]:
        return data[1]

    ret = {}

    client = mongdbClient()

    db_name = args['name']
    db = client[db_name]

    result = db.command("dbStats")
    result["collection_list"] = []
    for collection_name in db.list_collection_names():
        collection = db.command("collStats", collection_name)
        data = {
            "collection_name": collection_name,
            "count": collection.get("count"),  # 文档数
            "size": collection.get("size"),  # 内存中的大小
            "avg_obj_size": collection.get("avgObjSize"),  # 对象平均大小
            "storage_size": collection.get("storageSize"),  # 存储大小
            "capped": collection.get("capped"),
            "nindexes": collection.get("nindexes"),  # 索引数
            "total_index_size": collection.get("totalIndexSize"),  # 索引大小
        }
        result["collection_list"].append(data)
    
    return mw.returnJson(True,'ok', result)

def toDbBase(find):
    client = mongdbClient()
    db_admin = client.admin
    data_name = find['name']
    db = client[data_name]

    db.chat.insert_one({})
    user_roles = [{'role': 'dbOwner', 'db': data_name}, {'role': 'userAdmin', 'db': data_name}]
    try:
        db_admin.command("createUser", find['username'], pwd=find['password'], roles=user_roles)
    except Exception as e:
        db_admin.command("updateUser", find['username'], pwd=find['password'], roles=user_roles)
    return 1

def syncToDatabases():
    args = getArgs()
    data = checkArgs(args, ['type', 'ids'])
    if not data[0]:
        return data[1]

    stype = int(args['type'])
    sqlite_db = pSqliteDb('databases')
    n = 0

    if stype == 0:
        data = sqlite_db.field('id,name,username,password,accept').select()
        for value in data:
            result = toDbBase(value)
            if result == 1:
                n += 1
    else:
        data = json.loads(args['ids'])
        for value in data:
            find = sqlite_db.where("id=?", (value,)).field(
                'id,name,username,password,accept').find()
            # print find
            result = toDbBase(find)
            if result == 1:
                n += 1
    msg = mw.getInfo('本次共同步了{1}个数据库!', (str(n),))
    return mw.returnJson(True, msg)


def getAllRole():
    mongo_role = {
        # 数据库用户角色
        "read": "读取数据(read)",
        "readWrite": "读取和写入数据(readWrite)",
        # 数据库管理角色
        # "dbAdmin": "数据库管理员",
        "dbOwner": "数据库所有者(dbOwner)",
        "userAdmin": "用户管理员(userAdmin)",
        # 集群管理角色
        # "clusterAdmin": "集群管理员",
        # "clusterManager": "集群管理器",
        # "clusterMonitor": "集群监视器",
        # "hostManager": "主机管理员",
        # 备份和恢复角色
        # "backup": "备份数据",
        # "restore": "还原数据",
        # 所有数据库角色
        # "readAnyDatabase": "任意数据库读取",
        # "readWriteAnyDatabase": "任意数据库读取和写入",
        # "userAdminAnyDatabase": "任意数据库用户管理员",
        # "dbAdminAnyDatabase": "任意数据库管理员",
        # 超级用户角色
        # "root": "超级管理员",
        # 内部角色
        # "__queryableBackup": "可查询备份",
        # "__system": "系统角色",
        # "enableSharding": "启用分片",
    }

    client = mongdbClient()
    db = client.admin

    # 获取所有角色
    role_data = db.command('rolesInfo', showBuiltinRoles=True)
    result = []
    for role in role_data["roles"]:
        if mongo_role.get(role["role"]) is not None:
            role["name"] = mongo_role.get(role["role"])
            result.append(role)
    return mw.returnJson(True, 'ok', result)

def getDbAccess():
    args = getArgs()
    data = checkArgs(args, ['username'])
    if not data[0]:
        return data[1]

    client = mongdbClient()
    db = client.admin
    username = args['username']

    mongo_role = {
        # 数据库用户角色
        "read": "读取数据(read)",
        "readWrite": "读取和写入数据(readWrite)",
        # 数据库管理角色
        # "dbAdmin": "数据库管理员",
        "dbOwner": "数据库所有者(dbOwner)",
        "userAdmin": "用户管理员(userAdmin)",
        # 集群管理角色
        # "clusterAdmin": "集群管理员",
        # "clusterManager": "集群管理器",
        # "clusterMonitor": "集群监视器",
        # "hostManager": "主机管理员",
        # 备份和恢复角色
        # "backup": "备份数据",
        # "restore": "还原数据",
        # 所有数据库角色
        # "readAnyDatabase": "任意数据库读取",
        # "readWriteAnyDatabase": "任意数据库读取和写入",
        # "userAdminAnyDatabase": "任意数据库用户管理员",
        # "dbAdminAnyDatabase": "任意数据库管理员",
        # 超级用户角色
        # "root": "超级管理员",
        # 内部角色
        # "__queryableBackup": "可查询备份",
        # "__system": "系统角色",
        # "enableSharding": "启用分片",
    }

    role_data = db.command('rolesInfo', showBuiltinRoles=True)
    all_role_list = []
    for role in role_data["roles"]:
        if mongo_role.get(role["role"]) is not None:
            role["name"] = mongo_role.get(role["role"])
            all_role_list.append(role)

    result = {
        "user": username,
        "db": username,
        "roles": [],
        "all_roles":all_role_list,
    }

    user_data = db.command('usersInfo', username)
    if user_data:
        if len(user_data["users"]) != 0:
            user = user_data["users"][0]
            result["user"] = user.get("user", username)
            result["db"] = user.get("db", username)
            result["roles"] = user.get("roles", [])

    return mw.returnJson(True, 'ok', result)

def setDbAccess():
    args = getArgs()
    data = checkArgs(args, ['username', 'select','name'])
    if not data[0]:
        return data[1]
    username = args['username']
    select = args['select']
    name = args['name']

    mg_pass = pSqliteDb('config').where('id=?', (1,)).getField('mg_root')

    # user_rules = [
    #     {'role': 'root', 'db': 'admin'},
    #     {'role': 'clusterAdmin', 'db': 'admin'},
    #     {'role': 'readAnyDatabase', 'db': 'admin'},
    #     {'role': 'readWriteAnyDatabase', 'db': 'admin'},
    #     {'role': 'userAdminAnyDatabase', 'db': 'admin'},
    #     {'role': 'dbAdminAnyDatabase', 'db': 'admin'},
    #     {'role': 'userAdmin', 'db': 'admin'},
    #     {'role': 'dbAdmin', 'db': 'admin'}
    # ]

    user_roles = []
    select_role = select.split(',')
    for role in select_role:
        t = {}
        t['role'] = role
        t['db'] = name
        user_roles.append(t)

    client = mongdbClient()
    db = client.admin

    try:
        db.command("updateUser", username, pwd=mg_pass, roles=user_roles)
    except Exception as e:
        db.command('dropUser',username)
        db.command("createUser", username, pwd=mg_pass, roles=user_roles)

    return mw.returnJson(True, '设置成功!')

def testData():
    '''
    cd /www/server/mdserver-web && source bin/activate && python3 /www/server/mdserver-web/plugins/mongodb/index.py test_data
    '''
    import pymongo
    from pymongo import ReadPreference
    
    client = mongdbClient()

    db = client.test
    col = db["demo"]

    rndStr = mw.getRandomString(10)
    insert_dict = { "name": "v1", "value": rndStr}
    x = col.insert_one(insert_dict)
    print(x)


def test():
    '''

    cd /www/server/mdserver-web && source bin/activate && python3 /www/server/mdserver-web/plugins/mongodb/index.py test
    python3 plugins/mongodb/index.py test
    '''
    # https://pymongo.readthedocs.io/en/stable/examples/high_availability.html
    # import pymongo
    # from pymongo import ReadPreference
    
    # client = mongdbClient()

    # db = client.admin

    # print(db['users'])
    # r = db.command("grantRolesToUser", "root",
    #                  roles=["root"])
    # print(r)
    # users_collection = db['users']
    # print(users_collection)

    # mg_pass = mw.getRandomString(10)
    # r = db.command("createUser", "root1", pwd=mg_pass, roles=["root"])
    # print(r)
    # config = {
    #     '_id': 'test',
    #     'members': [
    #         # 'priority': 10 
    #         {'_id': 0, 'host': '154.21.203.138:27017'},
    #         {'_id': 1, 'host': '154.12.53.216:27017'},
    #     ]
    # }

    # rsStatus = client.admin.command('replSetInitiate',config)
    # print(rsStatus)

    # 需要通过命令行操作
    # rs.initiate({
    #     _id: 'test',
    #     members: [
    #     {
    #         _id: 1,
    #         host: '154.21.203.138:27017',
    #         priority: 2
    #     }, 
    #     {
    #         _id: 2,
    #         host: '154.12.53.216:27017',
    #         priority: 1
    #     }

    #     ]
    # });

    # > rs.status();  // 查询状态
    # // "stateStr" : "PRIMARY", 主节点
    # // "stateStr" : "SECONDARY", 副本节点

    # > rs.add({"_id":3, "host":"127.0.0.1:27318","priority":0,"votes":0});


    # serverStatus = db.command('serverStatus')
    # print(serverStatus)
    
    return mw.returnJson(True, 'OK')

    

def initdStatus():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    shell_cmd = 'systemctl status mongodb | grep loaded | grep "enabled;"'
    data = mw.execShell(shell_cmd)
    if data[0] == '':
        return 'fail'
    return 'ok'


def initdInstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl enable mongodb')
    return 'ok'


def initdUinstall():
    if mw.isAppleSystem():
        return "Apple Computer does not support"

    mw.execShell('systemctl disable mongodb')
    return 'ok'


def runLog():
    f = getServerDir() + '/logs/mongodb.log'
    if os.path.exists(f):
        return f
    return getServerDir() + '/logs.pl'


def installPreInspection(version):
    if mw.isAppleSystem():
        return 'ok'

    sys = mw.execShell(
        "cat /etc/*-release | grep PRETTY_NAME |awk -F = '{print $2}' | awk -F '\"' '{print $2}'| awk '{print $1}'")

    if sys[1] != '':
        return '暂时不支持该系统'

    sys_id = mw.execShell(
        "cat /etc/*-release | grep VERSION_ID | awk -F = '{print $2}' | awk -F '\"' '{print $2}'")

    sysName = sys[0].strip().lower()
    sysId = sys_id[0].strip()

    supportOs = ['centos', 'ubuntu', 'debian', 'opensuse']
    if not sysName in supportOs:
        return '暂时仅支持{}'.format(','.join(supportOs))
    return 'ok'

if __name__ == "__main__":
    func = sys.argv[1]

    version = "4.4"
    if (len(sys.argv) > 2):
        version = sys.argv[2]

    if func == 'status':
        print(status())
    elif func == 'start':
        print(start())
    elif func == 'stop':
        print(stop())
    elif func == 'restart':
        print(restart())
    elif func == 'reload':
        print(reload())
    elif func == 'install_pre_inspection':
        print(installPreInspection(version))
    elif func == 'initd_status':
        print(initdStatus())
    elif func == 'initd_install':
        print(initdInstall())
    elif func == 'initd_uninstall':
        print(initdUinstall())
    elif func == 'run_info':
        print(runInfo())
    elif func == 'run_doc_info':
        print(runDocInfo())
    elif func == 'run_repl_info':
        print(runReplInfo())
    elif func == 'conf':
        print(getConf())
    elif func == 'get_config':
        print(getConfig())
    elif func == 'set_config':
        print(saveConfig())
    elif func == 'set_config_auth':
        print(setConfigAuth())
    elif func == 'get_db_list':
        print(getDbList())
    elif func == 'add_db':
        print(addDb())
    elif func == 'del_db':
        print(delDb())
    elif func == 'set_root_pwd':
        print(setRootPwd())
    elif func == 'set_user_pwd':
        print(setUserPwd())
    elif func == 'sync_get_databases':
        print(syncGetDatabases())
    elif func == 'sync_to_databases':
        print(syncToDatabases())
    elif func == 'set_db_ps':
        print(setDbPs())
    elif func == 'get_db_info':
        print(getDbInfo())
    elif func == 'get_all_role':
        print(getAllRole())
    elif func == 'get_db_access':
        print(getDbAccess())
    elif func == 'set_db_access':
        print(setDbAccess())
    elif func == 'run_log':
        print(runLog())
    elif func == 'test':
        print(test())
    elif func == 'test_data':
        print(testData())
    else:
        print('error')
