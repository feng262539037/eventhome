#coding:utf-8
import base64
import hashlib
import json
import datetime,time
from django.contrib import auth
from rest_framework.decorators import api_view
from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.db import connection
from models import *
# Create your views here.

def shanchu(request):
    username = request.POST.get('username', None)
    User.objects.filter(username=username).delete()

    return HttpResponse('123')


#校验签名方法
'''
校验内容：
1、根据username，查询数据库user表，校验user存在
2、根据user，查询数据库usertoken表，校验token = 入参token
   同时校验sign为必填
3、校验random = 5位
4、校验server_sign = sign
校验结果：
在控制台打印server_sign
如果server_sign = sign返回flag = True，否则flag = False
'''
def check_sign(headers_dic, para_dic):
    flag = False
    random = headers_dic.get('HTTP_RANDOM', None)
    token = headers_dic.get('HTTP_TOKEN', None)
    username = para_dic.get('username', None)
    sign = para_dic.get('sign', None)

    user = User.objects.filter(username=username)
    if user.exists():
        #只能用get，不能用filter
        if token == Token.objects.get(user = user.first()).key and sign:
            if len(random) == 5:
                para_str = ''
                para_list = []
                for k, v in para_dic.items():
                    if k not in ['sign', 'username']:
                        para_list.append(k + '=' + v)

                para_list.sort()
                #注意列表转字符串的写法
                para_str = '&'.join(para_list)
                #注意前和后之间，用%链接
                md5_str = '%spara=%s%s'% (token, para_str, random)
                print 'md5_str=' + md5_str

                md5 = hashlib.md5()
                md5.update(md5_str.encode(encoding="utf-8"))
                server_sign = md5.hexdigest()
                print 'server_sign=' + server_sign

                if sign == server_sign:
                    flag = True
    return flag

#系统管理员登陆接口
'''
校验内容：
1、校验请求类型
2、校验username、password必填
3、校验传入的password是base64加密后的
4、校验username、password正确
校验结果，返回该user对应的token、对应的id
数据操作：
'''
@api_view(['POST'],)
def register(request):
    result = {}
    username = request.POST.get('username')
    password = request.POST.get('password')

    if username and password:
        #如果传入的密码，不是有效的base64加密后的
        try:
            #注意需求
            password = base64.decodestring(password)[3:]
        except:
            password = password
        user = auth.authenticate(username = username, password = password)
        if user:
            #必须用get，不能用filter，因为要通过获取到的对象.属性，获取key值
            token = Token.objects.get(user = user).key
            uid = user.id
            result = {'error_code': 0, 'token': token, 'uid': uid}
        else:
            result = {'error_code': 10000}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#添加会议接口
'''
校验内容：
1、校验请求类型
2、校验username、title、address、time必填
3、校验签名正确
4、校验title唯一
5、校验status的类型正确
6、校验event_time格式正确
7、校验event_time大于当前时间
校验结果，按接口文档返回对应参数
数据操作：
'''
@api_view(['POST'],)
def add_event(request):
    result = {}
    username = request.POST.get('username', None)
    title = request.POST.get('title', None)
    limit = request.POST.get('limit', 200)
    #这个默认值0，必须是字符串。因为下面对status的范围进行判断时，也是字符串
    status = request.POST.get('status', '0')
    address = request.POST.get('address', None)
    #最好不用time，避免和系统的变量相同
    event_time = request.POST.get('time', None)

    if username and title and address and time:
        if check_sign(request.META, request.POST):
            event = Event.objects.filter(title = title)
            if not event.exists():
                if status in ('0', '1', '2'):
                    #如果传入的时间格式错误,time.strptime会报错
                    try:
                        t = time.strptime(event_time, '%Y-%m-%d %H:%M:%S')
                    except:
                        # 需求里没有这个错误码，我们随便给的
                        result = {'error_code': 100012}
                        return JsonResponse(result)
                    #如果传入的时间大于当前时间
                    if time.mktime(t) > time.time():
                        data = {}
                        event = Event.objects.create(title = title, limit = limit, status = status,
                                             address = address, time = event_time)
                        data['event_id'] = event.id
                        data['status'] = event.status
                        result = {'error_code': 0, 'data': data}
                    else:
                        #需求里没有这个错误码，我们随便给的
                        result = {'error_code': 100013}
                else:
                    result = {'error_code': 10003}
            else:
                result = {'error_code': 10002}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}

    return JsonResponse(result)

#查询会议列表接口
'''
校验内容：
1、请求类型
2、username必填
3、校验签名
4、title非必填
(1)没输入title，返回QuerySet对象，查询结果集
(2)输入title  -- 模糊匹配，返回QuerySet对象，查询结果集
5、对返回的结果集的长度，进行判断
(1)长度大于0，按接口文档返回对应参数
(2)否则，会议不存在
校验结果，按接口文档返回对应参数
数据操作：
'''
@api_view(['GET'],)
def get_eventlist(request):
    result = {}
    username = request.GET.get('username', None)
    title = request.GET.get('title', None)

    if username:
        if check_sign(request.META,request.GET):
            #没输入title，返回events集合
            if not title:
                events = Event.objects.all()
            #已输入title，返回events列表
            else:
                events = Event.objects.filter(title__contains= title)

            if len(events) > 0:
                event_list = []
                #循环events列表，每一个event是一个对象实例
                for event in events:
                    id = event.id
                    title = event.title
                    status = event.status
                    event_list.append({'id': id, 'title': title, 'status': status})
                result = {'error_code': 0, 'event_list': event_list}
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#查询会议详情信息接口
'''
校验内容：
1、请求类型
2、username、会议id，必填
3、校验会议id
校验结果，按接口文档返回对应参数
数据操作：
'''
@api_view(['GET'],)
def get_eventdetail(request):
    result = {}
    username = request.GET.get('username', None)
    id = request.GET.get('id', None)

    if username and id:
        if check_sign(request.META, request.GET):
            event = Event.objects.filter(id = id)
            if event.exists():
                #event = Event.objects.get(id = id)
                event_detail = {}
                event_detail['id'] = event.first().id
                event_detail['title'] = event.first().title
                event_detail['status'] = event.first().status
                event_detail['limit'] = event.first().limit
                event_detail['address'] = event.first().address
                event_detail['time'] = event.first().time
                result = {'error_code': 0, 'event_detail': event_detail}
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#修改会议状态接口
'''
校验内容：
1、校验请求类型
2、校验username、id、status,必填
3、校验签名
4、校验会议id
5、校验status类型
6、修改status
校验结果，按接口文档返回对应参数
数据操作：
'''
@api_view(['POST'],)
def set_status(request):
    result = {}
    username = request.POST.get('username', None)
    id = request.POST.get('id', None)
    status = request.POST.get('status', None)

    if username and id and status:
        if check_sign(request.META, request.POST):
            event = Event.objects.filter(id = id)
            #注意exitsts(),最后有个括号
            if event.exists():
                if status in ('0', '1', '2'):
                    #注意有个坑，不能用event.first()去更新！！！

                    #更新方式一：用get查询到一个model对象
                    #event = Event.objects.get(id = id)
                    #直接把传入的status，赋值给，对象.属性
                    #event.status = status
                    #调用save()方法
                    #event.save()
                    #更新方式二：用filter查询到，直接用update方法更新属性
                    event.update(status=status)
                    result = {'error_code': 0}
                else:
                    result = {'error_code': 10003}
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#为指定会议新增嘉宾接口
'''
校验内容：
1、校验请求类型
2、校验username、会议id、嘉宾name，嘉宾phone_number，必填
3、校验签名
4、校验会议是否存在
5、校验嘉宾是否存在


校验结果，按接口文档返回对应参数
数据操作：
'''
@api_view(['POST'],)
def add_guest(request):
    result = {}
    username = request.POST.get('username', None)
    id = request.POST.get('id', None)
    name = request.POST.get('name', None)
    phone_number = request.POST.get('phone_number', None)
    e_mail = request.POST.get('e_mail', None)

    if username and id and name and phone_number:
        if check_sign(request.META, request.POST):
            #在Event表中，根据会议的id，用filter，查询会议集合（唯一的）
            event = Event.objects.filter(id = id)
            #在Guest表中，根据手机号，用filter，查询嘉宾集合（唯一的）
            guest = Guest.objects.filter(phone_number=phone_number)
            #***在Event_Guest表中，根据会议对象，查询会议id已经有的嘉宾数量
            count = Guest.objects.filter(event=event.first()).count()
            #会议存在Event表中
            if event.exists():
                #嘉宾不在Guest表中
                if not guest.exists():
                    #会议id已有的嘉宾数量 < 会议id设定的嘉宾上限
                    if count < event.first().limit:
                        #在Guest表中，添加嘉宾对象
                        g = Guest.objects.create(name=name, phone_number=phone_number, e_mail=e_mail)
                        #***同时，在Event_Guest表中，把嘉宾和会议id关联
                        g.event.add(event.first())
                        result = {'error_code': 0, "data": {"event_id": id, "guest_id": g.id}}
                    #实际嘉宾数量 > 这个会议的上限
                    else:
                        result = {'error_code': 10006}
                #嘉宾在Guest表中
                else:
                    #方式一：***在Event_Guest表中，根据嘉宾，查询这个嘉宾关联的会议的id
                    #用values_list，返回元组列表，如：[(1,), (2,), (3,)]
                    #events_id = guest.first().event.all().values_list('id')
                    #方式二：多表关联查询：在Event_Guest表中，根据嘉宾，查询这个嘉宾关联的会议的id
                    # events_id = guest.values_list('event__id')
                    #***方式三：多表关联查询，嘉宾已经关联的会议events_id
                    events_id = guest.values('event__id')
                    e_id_list = []
                    for i in events_id:
                        event_id = i.get('event__id')
                        e_id_list.append(event_id)
                    #***注意：把会议id转成int！！！
                    if int(id) not in e_id_list:
                        if count < event.first().limit:
                            #在Event_Guest表中，添加相对应的会议对象
                            guest.first().event.add(event.first())
                            result = {'error_code': 0, "data": {"event_id": id, "guest_id": guest.first().id}}
                        # 实际嘉宾数量 > 这个会议的上限
                        else:
                            result = {'error_code': 10006}
                    #会议嘉宾已存在
                    else:
                        result = {'error_code': 10005}
            #会议不在Event表中
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#查询会议嘉宾接口
'''
校验内容：
1、请求类型
2、username、event_id必填
3、校验签名
4、校验会议是否存在
5、phone_number非必填
(1)输入phone_number，返回QuerySet对象，查询结果集，返回该会议的这个嘉宾
(2)没输入phone_number，返回QuerySet对象，查询结果集，返回该会议的所有嘉宾
6、校验会议中是否有嘉宾
'''
@api_view(['GET'],)
def get_guestlist(request):
    result = {}
    username = request.GET.get('username', None)
    event_id = request.GET.get('id', None)
    phone_number = request.GET.get('phone_number', None)

    if username and event_id:
        if check_sign(request.META, request.GET):
            event = Event.objects.filter(id = event_id)
            if event.exists():
                #输入phone_number
                if phone_number:
                    #在Guest表中，根据会议对象和phone_number，查询这个嘉宾
                    guests = Guest.objects.filter(event=event.first(), phone_number=phone_number)
                #没输入phone_number
                else:
                    #在Guest表中，根据会议对象，查这个会议的所有嘉宾
                    guests = Guest.objects.filter(event=event.first())
                if guests.exists():
                    guest_list = []
                    for guest in guests:
                        guest_dic = {}
                        guest_dic['guest_id'] = guest.id
                        guest_dic['name'] = guest.name
                        guest_dic['phone_number'] = guest.phone_number
                        guest_dic['e-mail'] = guest.e_mail
                        guest_list.append(guest_dic)
                    result = {'error_code': 0, 'guest_list': guest_list}
                else:
                    result = {'error_code': 10007}
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#嘉宾签到
@api_view(['POST', ])
def sign(request):
    event_id = request.POST.get('id', None)
    phone_number = request.POST.get('phone_number', None)
    username = request.POST.get('username', None)

    if event_id and phone_number and username:
        if check_sign(request.META, request.POST):
            event = Event.objects.filter(id=event_id)
            if event.exists():
                n_time = time.time()
                e_time = time.mktime(event.first().time.timetuple())
                print 'e_time=%s' %e_time
                if event.first().status != '2' and n_time < e_time:
                    #***1、根据手机号，在Guest表中查询这个嘉宾
                    #***2、同时，根据event对象，判断嘉宾是否关联了会议
                    #***最终结论：嘉宾在Guest表中 and 这个嘉宾和这个会议关联！！！相当于and
                    guest = Guest.objects.filter(phone_number=phone_number, event=event.first())
                    if guest.exists():
                        query = "SELECT sign FROM api_guest_event where guest_id=%s and event_id=%s" \
                                %(guest.first().id, event_id)
                        #获取一个数据库游标对象
                        cursor = connection.cursor()
                        #返回值为int！！！，标识受影响的行数！！！
                        cursor.execute(query)
                        #返回元组
                        is_sign = cursor.fetchone()[0]
                        if is_sign == 0:
                            query = "UPDATE api_guest_event SET sign=1 where guest_id=%s and event_id=%s" \
                                %(guest.first().id, event_id)
                            cursor.execute(query)
                            result = {'error_code': 0}
                        else:
                            result = {'error_code': 10009}
                    #***如果嘉宾不在Guest表中报错
                    #***如果嘉宾在Guest表中，但是嘉宾和会议不匹配，报错
                    else:
                        result = {'error_code': 10008}
                else:
                    result = {'error_code': 10010}
            else:
                result = {'error_code': 10004}
        else:
            result = {'error_code': 10011}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#生成签名
'''
校验内容：
1、校验请求类型
2、校验random、token、username必填
2、校验user存在
3、校验token正确
4、校验random长度等于5
校验结果，
MD5加密前的字符串:md5_str
通过代码进行MD5加密后的数字签名:server_sign
数据操作：
'''
@api_view(['POST'],)
def create_sign(request):
    result = {}

    random = request.META.get('HTTP_RANDOM')
    token = request.META.get('HTTP_TOKEN')

    username = request.POST.get('username')

    #备注：下面不需要对para_dic做判断，因为para_dic中必然有username
    para_dic = request.POST
    #print para_dic

    if random and token and username:
        user = User.objects.filter(username = username)
        if user.exists():
            #注意一定要用get，而不能用filter，因为要获取model对象的属性值
            if token == Token.objects.get(user = user).key:
                if len(random) == 5:
                    para_list = []
                    para_str = ''
                    #注意循环字典的k
                    # ey和value：加上.items
                    #循环字典的key和value，获取的是列表
                    for k, v in para_dic.items():
                        #print k + ' ' + v
                        if k not in ['username']:
                            para_list.append(k + '=' + v)
                    #打印：去除username和sign之后的列表
                    #print para_list
                    #对列表进行升序排列
                    para_list.sort()
                    #并打印
                    #print para_list
                    #把列表转成字符串
                    para_str = '&'.join(para_list)
                    #并打印
                    #print para_str
                    #%s的个数=后面参数的个数
                    md5_str = "%spara=%s%s" % (token, para_str, random)
                    #print md5_str
                    result['md5_str'] = md5_str

                    md5 = hashlib.md5()
                    md5.update(md5_str.encode(encoding="utf-8"))
                    server_sign = md5.hexdigest()
                    result['server_sign'] = server_sign
                else:
                    result = {'error_code': 'random长度错误'}
            else:
                result = {'error_code': 'token错误'}
        else:
            result = {'error_code': 'user不存在'}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)

#校验签名
'''
校验内容：
1、校验请求类型
2、校验random、token、username、sign必填
2、校验user存在
3、校验token正确
4、校验random长度等于5
校验结果，
server_sign 是否等于 sign
数据操作：
'''
@api_view(['POST'],)
def review_sign(request):
    result = {}

    random = request.META.get('HTTP_RANDOM')
    token = request.META.get('HTTP_TOKEN')

    username = request.POST.get('username')
    #相比上一个create_sign接口,多取了一个sign值
    sign = request.POST.get('sign')

    # 备注：下面不需要对para_dic做判断，因为para_dic中必然有username
    para_dic = request.POST

    if random and token and username and sign:
        user = User.objects.filter(username=username)
        if user.exists():
            # 注意一定要用get，而不能用filter，因为要获取model对象的属性值
            if token == Token.objects.get(user=user).key:
                if len(random) == 5:
                    para_list = []
                    para_str = ''
                    # 注意循环字典的key和value：加上.items()
                    for k, v in para_dic.items():
                        if k not in ['username', 'sign']:
                            para_list.append(k + '=' + v)
                    para_list.sort()
                    para_str = '&'.join(para_list)
                    # %s的个数=后面参数的个数
                    md5_str = "%spara=%s%s" % (token, para_str, random)

                    md5 = hashlib.md5()
                    md5.update(md5_str.encode(encoding="utf-8"))
                    server_sign = md5.hexdigest()
                    if sign == server_sign:
                        result = {'error_code': 'sign校验通过'}
                    else:
                        result = {'error_code': 'sign校验失败'}
                else:
                    result = {'error_code': 'random长度错误'}
            else:
                result = {'error_code': 'token错误'}
        else:
            result = {'error_code': 'user不存在'}
    else:
        result = {'error_code': 10001}
    return JsonResponse(result)



