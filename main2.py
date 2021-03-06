#-*- coding: UTF-8 -*- 
import os,sys,re,json
import cx_Oracle
from socket import inet_aton, inet_ntoa
from struct import unpack, pack
from IPy import IP
#继续main.py部分的功能，完成全部决策
#编辑于2018年10月25日

def _check_ip(ip_add):#检验ip地址字符串是否合法
    """
    common func
    """
    p = re.compile(r'^(([01]?[\d]{1,2})|(2[0-4][\d])|(25[0-5]))' \
                   r'(\.(([01]?[\d]{1,2})|(2[0-4][\d])|(25[0-5]))){3}(\/(\d+))?$')

    return p.search(str(ip_add)) is not None


def calcSubnet(ip_add, mask):#根据ip地址和子网掩码计算子网地址（不带网络前缀的形式），如192.168.1.128
    """
    Return the sub net of the network
    eisoopylib.calcSubnet("192.168.0.1", "255.255.255.0")
    192.168.0.0
    etc.
    """
    if _check_ip(ip_add) and _check_ip (mask):
        ip_num, = unpack("!I", inet_aton(ip_add))
        mask_num, = unpack("!I", inet_aton(mask))
        subnet_num = ip_num & mask_num
        return inet_ntoa (pack ("!I", subnet_num))
    else:
        return False

def NumberOf1(n):#计算某个10进制数转换为2进制数之后，其中1的个数
    if n< 0:
        n = n&0xffffffff
    count = 0
    while n:
        count += 1
        n = (n-1)&n
    return count

def mask2prefix(mask):#输入为字符串（子网掩码），输出为整数（网络前缀），错误处理欠缺
    prefix = 0
    res = mask.split('.',3)
    for item in res:
        prefix += NumberOf1(int(item))
    return prefix



#第一个参数，含子网的json文件
#第二个参数，数据库连接信息
#第三个参数，他们的数据库连接信息
command_arguments = sys.argv
if not (len(command_arguments)==4):
    print('error:incorrect argument')
    sys.exit(1)
filename = command_arguments[1]
dbconfigs = command_arguments[2]
dbconfigs_target = command_arguments[3]
#connect to the database
try:
    conn = cx_Oracle.connect(dbconfigs)
except:
    print('Exception:can not connect to the database')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)
cursor = conn.cursor()

try:
    conn_target = cx_Oracle.connect(dbconfigs_target)
except:
    print('Exception:can not connect to the database')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)
cursor_target = conn_target.cursor()

#get username
m_user = re.findall('^(.*)/(.*)@(.*):(.*)/(.*)$',dbconfigs.strip())
try:
    db_username = m_user[0][0].upper()
except:
    print('Exception:can not get database username')
    sys.exit(1)

"""start"""
def get_topo_ips(items):
    """obtain relevant routers' ip based on subnet"""
    composite_items = []
    if items == []:
        return -1
    for item in items:
        atom_item = []
        router_flag = 0
        atom_item.append(item)
        net_prefix = item.split(',')[1]
        net = net_prefix.split('/')[0]
        mask = update_mask(int(net_prefix.split('/')[1]))
        default_gateway = item.split(',')[2]
        try:
            cursor_target.execute('select IP,NET from ROUTER')
            routers = cursor_target.fetchall() 
        except Exception as err:
            print(err)
            return -1
        #read data from ROUTER
        if cursor_target.rowcount == 0:
            return -1
        for router in routers:
            ips_str = str(router[0])
            if router[1]!='Unknown': #the net field is not empty
                if router[1]==net:
                    router_flag = 1
                    atom_item.append(ips_str.split(',')[0])   #get the first ip
                    composite_items.append(atom_item)
                    break
            ips = ips_str.split(',')
            for ip in ips:
                router_net = str(IP(ip).make_net(mask)).split('/',1)[0]
                if router_net == net:
                    router_flag = 1
                    atom_item.append(ip)
                    composite_items.append(atom_item)
                    break
            if router_flag == 1:
                break

        #not get router ip
        if router_flag == 0:
            if default_gateway!='Unknown':
                atom_item.append(default_gateway)
                composite_items.append(atom_item)
                continue
            net_split = net.split('.')
            ip = net_split[0]+'.'+net_split[1]+'.'+net_split[2]+'.1'
            atom_item.append(ip)
            composite_items.append(atom_item)

    return composite_items

def parse_items(double_items):
    ip_item = []
    if double_items == [] or double_items == -1:
        return -1
    for items in double_items:
        host_ip = items[0].split(',')[0]
        router_ip = items[1]
        ips = host_ip + ',' + router_ip
        ip_item.append(ips)
    return ip_item

"""end"""

def update_mask(mask_int):
    """Transfer number to mask"""
    bin_arr = ['0' for i in range(32)]
    for i in range(mask_int):
        bin_arr[i] = '1'
    tmpmask = [''.join(bin_arr[i * 8:i * 8 + 8]) for i in range(4)]
    tmpmask = [str(int(tmpstr,2)) for tmpstr in tmpmask]
    return '.'.join(tmpmask)


#读出带掩码的json文件中信息
#暂时认为输入的是json文件，如果不是的话再改
#json格式，示例：
#{'hosts': [{'ip': '192.168.1.52', 'mask': '255.255.255.0', 'gateway': '192.168.1.1'}, {'ip': '192.168.1.123', 'mask': '255.255.255.128', 'gateway': '192.168.1.1'}, {'ip': '192.168.1.157', 'mask': '255.255.255.0', 'gateway': '192.168.1.1'}]}
with open(filename,"r") as load_f:
    load_dict = json.load(load_f)
    print(load_dict)

ip_mask = []#存放ip和mask对
for item in load_dict['hosts']:
    print(item)
    ip_mask.append(item)
print(ip_mask)
#这里ip_mask和load_dict['hosts']等同，不管输入是什么形式，都把它转化为ip_mask的这种形式，方便后续处理
prefix = 0
for item in ip_mask:
    #计算该节点所属的子网地址（带网络前缀的形式），如192.168.1.128/25
    if item["mask"] == "" or item["gateway"] == "":
        #取消未获取到子网掩码的ip的待选资格，isagent置为3，认为它们不在线或者未被部署个体节点程序
        try:
            cursor.execute("""
            update {username}.HOST set ISAGENT=3 where IP=:ip
            """.format(username=db_username),ip=item["ip"])
        except:
            print("Error:can not update")
            error_info = sys.exc_info()
            if len(error_info) > 1:
                print(str(error_info[0]) + ' ' + str(error_info[1]))
        continue
    prefix = mask2prefix(item["mask"])
    tmp_sub = calcSubnet(item["ip"],item["mask"])
    if tmp_sub == False:
        print("error: incorrect format of ip or netmask, ignore it")
        continue
    subnet = tmp_sub + '/' + str(prefix)
    #算出子网，下一步准备写数据库（只更新它们的子网字段）
    try:
        cursor.execute("""
        update {username}.HOST set HMASK=:sb where IP=:ip
        """.format(username=db_username),sb=subnet,ip=item["ip"])
    except:
        print("Error:can not update a specified ip's subnet")
        error_info = sys.exc_info()
        if len(error_info) > 1:
            print(str(error_info[0]) + ' ' + str(error_info[1]))
    #剔除默认网关的参选权，isAgent为5代表默认网关
    try:
        cursor.execute("""
        update {username}.HOST set ISAGENT=5 where IP=:gateway
        """.format(username=db_username),gateway=item["gateway"])
    except:
        print("Error:can not update gateway information")
        error_info = sys.exc_info()
        if len(error_info) > 1:
            print(str(error_info[0]) + ' ' + str(error_info[1]))
    print(subnet)

# Host 表增加Subnet字段 ××××
# 检验选举出的ip是否有效
# 已确定在同一个子网内的节点，仅部署1个agent
# 可能在同一个子网内的节点，仅部署1个agent

# 下面修改后的部分未经测试
try:
    cursor.execute("""
        select distinct NET from %s.AGENT
        """ %db_username)
except:
    print('error when selecting')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)
result_netfields = cursor.fetchall()# result_netfields中存放已经被选举为agent的主机所属的网段
print('已经有agent的子网：')
print(result_netfields)

#决策阶段1（选举）
print('***********决策阶段1（选举）*************')

hasNewHosts = 0#标志决策结果是否为新节点
#首先选取同时满足isAgent=0和isNew=1的节点
try:
    cursor.execute("""
        select IP as tIP,HWEIGHT as tHweight, HMASK as tSubnet  from %s.HOST where ISAGENT =0 and ISNEW = 1 and HISDEL = 0 ORDER BY HWEIGHT DESC  
            """ % db_username)
except:
    print('error when selecting')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)
result = cursor.fetchall()
AgentIP = []
NewNetFields = [] #确定的新agent的网段存在这里，方便最后更新Agent表
HighestWeight = 0#标志最高权重
HasThisNetField = 0;
if result:
    for host in result:
        objItem = {}
        #host[0]代表主机IP，host[1]代表主机权重
        #host[2]代表主机所属子网地址
        objItem["ip"] = host[0]
        objItem["Hweight"] = host[1]
        NetField = host[2]
        for item in result_netfields:# 检查此ip所属子网是否已经有选举出来的agent
            if NetField == item:
                # 一个子网最多有一个agent
                HasThisNetField = 1
                break
            elif HasThisNetField == 1:
                HasThisNetField = 0
        if HasThisNetField  == 1:
            continue
        if not AgentIP:#能走到这里的不仅是新节点而且属于新子网
            AgentIP.append(objItem["ip"])
            HighestWeight = objItem["Hweight"]
            NewNetFields.append(NetField)
        elif HighestWeight == objItem["Hweight"]:# AgentIP已经有内容，并与已有内容并列第一的
            AgentIP.append(objItem["ip"])
            NewNetFields.append(NetField)
        else:
            break
    if AgentIP:
        print('在新节点中决策出子节点')
        hasNewHosts = 1
    else:
        print('新节点中没有满足要求的子节点')
        hasNewHosts = 0#需要进入旧节点中决策。。
#倘若无新节点或者新节点中没有满足要求的子节点
if not result or not AgentIP:
    print('在旧节点中决策')
    try:
        cursor.execute("""
            select IP as tIP, HWEIGHT as tHweigh, HMASK as tSubnet from %s.HOST where ISAGENT = 0 and ISNEW = 0 and HISDEL = 0 ORDER BY HWEIGHT DESC           
            """ % db_username)
    except:
        print('error when selecting')
        error_info = sys.exc_info()
        if len(error_info) > 1:
            print(str(error_info[0]) + ' ' + str(error_info[1]))
        sys.exit(1)
    result = cursor.fetchall()
    HasThisNetField = 0#reinitialization
    if result:
        for host in result:
            objItem = {}
            #host[0]代表主机IP，host[1]代表主机权重
            #host[2]代表主机所属子网地址
            objItem["ip"] = host[0]
            objItem["Hweight"] = host[1]
            NetField = host[2]
            for item in result_netfields:# 检查此ip所属子网是否已经有选举出来的agent
                if NetField == item:
                    HasThisNetField = 1
                    break
                elif HasThisNetField == 1:
                    HasThisNetField = 0
            if HasThisNetField == 1:
                continue
            if not AgentIP:
                AgentIP.append(objItem["ip"])
                HighestWeight = objItem["Hweight"]
                NewNetFields.append(NetField)
            elif HighestWeight == objItem["Hweight"]:
                AgentIP.append(objItem["ip"])
                NewNetFields.append(NetField)
            else:
                break
        if AgentIP:
            print('在旧节点中决策出子节点')
            hasNewHosts = 0
        else:
            print('旧节点中没有满足需要的子节点，决策失败')
            hasNewHosts = 0

#注意，这里的AgentIP如果有内容的话，可能有多个属于同一个网段的，要去除重复的
FinalAgentIP = []#用于存放最终筛选剩下的
SubnetTmp = []#辅助数组
if AgentIP:
    print('筛去同一网段的')
    for item in AgentIP:
        try:
            cursor.execute("""
            select HMASK from %s.HOST where IP=:ip
            """ % db_username,ip=item)
        except:
            print('error when selecting')
            error_info = sys.exc_info()
            if len(error_info) > 1:
                print(str(error_info[0]) + ' ' + str(error_info[1]))
            sys.exit(1)
        result = cursor.fetchall()
        if result:
            if result[0][0] not in SubnetTmp:#ETC: result [('36.110.171.0/24',)] result[0] ('36.110.171.0/24') 36.110.171.0/24
                SubnetTmp.append(result[0][0])
                FinalAgentIP.append(item)
#如果筛完同网段的之后，什么都没有了，那就不筛了，就从同网段中的选取新个体节点，后面也不要将它们的isAgent置为2了。
#此处意为优先选取不同网段的主机作为新的子节点
if FinalAgentIP:
    print('从新子网中选取')
else:
    print('仍然从旧子网（已经含有其它子节点的）中选取')
    FinalAgentIP = AgentIP

print('最终选出来的是：')
print(FinalAgentIP)

#上面的内容尚未作详细测试
#更新部分要增加Agents表的更新
#决策阶段2（更新）
print('***********决策阶段2（更新）*************')
#如果决策不出来一切都免谈，HisDel在最终的最终才置为1，也就是整个一大轮决策结束的时候（改为在常驻进程的初始化步骤中执行）
print('将所有节点的isNew字段置为0')
try:
    cursor.execute("""
        update %s.HOST set ISNEW = 0
        """ % db_username)
except:
    print('error when updating')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)

#这个语句还没测
print('更新Agent表添加子网')
if SubnetTmp:
    for net in SubnetTmp:
        try:
            cursor.execute("""
            declare t_count number(10);
                            begin
                                select count(*) into t_count from {username}.AGENT where NET=:subnet;
                                if t_count=0 then
                                    insert into {username}.AGENT(NET) values(:subnet);
                                end if;
                            end;
            """.format(username=db_username),subnet=net)
        except:
            print('error when inserting')
            error_info = sys.exc_info()
            if len(error_info) > 1:
                print(str(error_info[0]) + ' ' + str(error_info[1]))
            sys.exit(1)

#将所有的在已经有agent的网段内的主机的isAgent置为2，且在这之前，它们的isAgent字段值为0
#但它们仍然有机会参与决策并被选举上（当没有其它不在已有子节点的子网中的主机时）
#这部分不要了
'''
try:
    cursor.execute("""
        update {username}.HOST set ISAGENT = 2 where ISAGENT = 0 and HMASK in(
        select NET from {username}.AGENT
        )""".format(username=db_username))
except:
    print('error when updating')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)
'''
#把真正选上了的isAgent置为1
for ip in FinalAgentIP:
    try:
        cursor.execute("""
        update %s.HOST set ISAGENT = 1 where IP=:newIndividualAgentIP 
        """ % db_username,newIndividualAgentIP = ip)
    except:
        print('error when updating')
        error_info = sys.exc_info()
        if len(error_info) > 1:
            print(str(error_info[0]) + ' ' + str(error_info[1]))
        sys.exit(1)

print('****************决策结束*****************')

#确认拓扑发现的参数，调用函数并传入一个（ip，子网地址，默认网关）的三元组数组
input_traid = []
traid_elem = ""
for ip in FinalAgentIP:
    traid_elem = ip
    try:
        cursor.execute("""
        select HMASK from {username}.HOST where IP=:tip
        """.format(username=db_username),tip=ip)
        result = cursor.fetchall()
        if result:
            tmp_str = ',' + result[0][0]
            traid_elem += tmp_str
        else:
            traid_elem += ','
    except:
        print('error when selecting HMASK from HOST')
        error_info = sys.exc_info()
        if len(error_info) > 1:
            print(str(error_info[0]) + ' ' + str(error_info[1]))
    has_gateway = False
    for item in ip_mask:
        if item['ip'] == ip and item['gateway']:
            tmp_str = ',' + item['gateway']
            traid_elem += tmp_str
            has_gateway = True
    if not has_gateway:
        tmp_str = ',' + 'Unknown'
        traid_elem += tmp_str
    input_traid.append(traid_elem)
print('待输入的三元组数组：')
print(input_traid)

ips_items = parse_items(get_topo_ips(input_traid))


# 根据子网内容设置主动探测参数
# 保存决策结果
#下面的未经测试
result = {}
task_list = []
ahost = []
phost = []
thost = []
activearg= []
task1 = {
    "type":"activeDetection",
}
task2 = {
    "type": "passiveDetection",
}
task3 = {
    "type": "topologicalDiscovery",
}
if FinalAgentIP:
    for ip in FinalAgentIP:
        try:
            cursor.execute("""
                    select HMASK from %s.HOST where IP=:tip
                    """ % db_username, tip=ip)
        except:
            print('error when selecting')
            error_info = sys.exc_info()
            if len(error_info) > 1:
                print(str(error_info[0]) + ' ' + str(error_info[1]))
            sys.exit(1)
        res = cursor.fetchall()
        activearg.append(res[0][0])
    print(activearg)
    for index in range(len(FinalAgentIP)):
        task1 = {
            "type": "activeDetection",
        }
        task2 = {
            "type": "passiveDetection",
        }
        task3 = {
            "type": "topologicalDiscovery",
        }
        ahost.append(FinalAgentIP[index]+":"+"8082")
        phost.append(FinalAgentIP[index]+":"+"8081")
        thost.append(FinalAgentIP[index]+":"+"9998")
        task1["taskArguments"] = activearg[index]
        task2["taskArguments"] = "-G 60 -P " + FinalAgentIP[index]
        task3["taskArguments"] = "127.0.0.1"
        if ips_items != -1:
            for ips_item in ips_items:
                host_ip = ips_item.split(',')[0]
                router_ip = ips_item.split(',')[1]
                if host_ip == FinalAgentIP[index]:
                    task3["taskArguments"] = router_ip
        tmpahost = []
        tmpphost = []
        tmpthost = []
        tmpahost.append(ahost[index])
        tmpphost.append(phost[index])
        tmpthost.append(thost[index])
        print("tmpahost:",tmpahost)
        print("tmpphost:",tmpphost)
        task1["hosts"] = tmpahost
        task2["hosts"] = tmpphost
        task3["hosts"] = tmpthost
        task_list.append(task1)
        task_list.append(task2)
        task_list.append(task3)
        print("task_list(1):", task_list);
        print("task_list(2):", task_list);
        print("task_list(3):", task_list);
result["tasks"] = task_list
result["hasNewHosts"] = hasNewHosts
try:
    with open("result.json","w") as f:
        json.dump(result,f)
        print("结果存储完成")
except:
    print('error when saving result')
    error_info = sys.exc_info()
    if len(error_info) > 1:
        print(str(error_info[0]) + ' ' + str(error_info[1]))
    sys.exit(1)


conn.commit()
cursor.close()
conn.close()
conn_target.commit()
cursor_target.close()
conn_target.close()