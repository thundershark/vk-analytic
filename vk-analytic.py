#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'salamander'
#взять средие(лушче медиану) от друзей пользователя по городу, возрасту и ВУЗу
import vkontakte
from pprint import pprint
from os.path import exists, isfile
import pickle, datetime
from copy import deepcopy

from handlers import logger, textViewer, auxMath


def getCredent(file):
    '''
    вытаскивает токен авторизации из файла credentials.txt
    @type param: file
    @rtype: str

    '''
    try:
        f = open(file,'r')
        line =  f.readline().strip()
        f.close()
    except FileNotFoundError:
        print("не найден файл с токеном авторизации")
        exit(1)
    return line



class analytic(object):
    #def __new__(cls, *args, **kwargs):
    #    if not hasattr(cls, 'instance'):
    #         cls.instance = super(analytic, cls).__new__(cls)
    #    return cls.instance
    __allUserFields='sex,bdate,city,country,photo_50,photo_100,photo_200_orig,photo_200,photo_400_orig,photo_max,photo_max_orig,online,online_mobile,lists,domain,has_mobile,contacts,connections,site,education,universities,schools,can_post,can_see_all_posts,can_see_audio,can_write_private_message,status,last_seen,common_count,relation,relatives,counters'
    __kitUserFields='sex,bdate,city,country,online,lists,domain,contacts,connections,site,education,universities,schools,can_post,can_see_all_posts,can_see_audio,can_write_private_message,status,last_seen,common_count,relation,relatives,counters'
    __researchFields='bdate,city,education,nickname,universities'
    #researchFields='bdate,city,universities,exports,connections,contacts'
    researchFields='bdate,city,universities'
    baseFields = 'first_name,last_name,uid'
    baseFields2 = 'online,user_id'
    baseFieldsFinally = baseFields + baseFields2
    __researchCmd = "friends.get(user_id=78340794,order='name',fields='bdate,city,education,nickname,universities')"
    t1 = 'friends.getMutual(source_uid=78340794, target_uid=11538362)'
    logtxt = []
    cache = {}
    cachPath = 'cacheLog'
    cacheLogFile = None

    def __warmingUpCache(self):
        """
        прогрев кеша из файла. Используется при инициализации экземпляра класса
        """
        try:
            self.cacheLogFile = open(self.cachPath,'rb+')
            while True:
                unpickleObj = pickle.load(self.cacheLogFile)
                unpickleObj = unpickleObj.popitem()
                self.cache[unpickleObj[0]]=unpickleObj[1]

        except FileNotFoundError:
            self.cacheLogFile = open(self.cachPath,'wb')
        except EOFError:
            pass

    def __logCache(self,cmd, response):
        pickle.dump({cmd:response},self.cacheLogFile)

    def __init__(self,tok,log=1,loggerObject=None):
        self.vk=vkontakte.API(token=tok)
        self.__warmingUpCache()
        self.logtxt=log
        if loggerObject is None:
            loggerObject = logger()
        self.logger = loggerObject
        self.social = socialAnalyze(self.vk,self.logtxt,self.logger)


    def getMutal(self,id1, id2):
        """
        возвращает общих друзей двух людей
        @rtype: list
        """
        res = self.vk.getMutual(source_uid=id1, target_uid=id2)
        return res

    def usersGet(self,ids, kitFields=__kitUserFields):
        """
        получение информации о некотором человеке
        """
        if isinstance(ids,list):
            ids=str(ids)[1:-1]
        info = []
        return self.vk.users.get(user_ids=ids, fields=kitFields)

    def eval(self,cmd):
        """
        выполняет произвольную команду к api vk
        @rtype: list
        """
        #print(cmd)
        #return eval('self.vk.%s'%cmd)
        return self.evalWithCache(cmd)

    def evalWithCache(self,cmd):
        """
        выполняет запрос к серверу vk с кешированием в оперативной памяти. (Кеш не обновляется со временем)
        @rtype: list
        """
        if cmd is '':
            return ''
        if cmd in self.cache:
            return self.cache[cmd]
        else:
            try:
                response = eval('self.vk.%s'%cmd)
            except vkontakte.VKError as e:
                print(e.description)
                if e.code==10:
                    print('вероятно произошла ошибка автрорзации')
                exit(1)
            self.cache[cmd]=response
            self.__logCache(cmd,response)
            return response


    def mainResearch(self, id: int, service=None, fields=researchFields):
        """
        пытается угадать возраст, пол и ВУЗ человека по его друзьям
        Используется метод максимума (среди друзей как правило, больше всего друзей с одного и того же ВУЗа, того же возраста и из того же города, что и сам человек
        @rtype: str
        """
        peopleList = self.eval("friends.get(user_id=%s,order='name', fields='%s')"%(str(id),fields))
        #частотные словари
        berd = {}
        univers = {}
        city = {}
        friendsNumber = len(peopleList)
        #добавление данных в частотные словари
        for people in peopleList:
            assert isinstance(people,dict)
            auxMath.addToDict(city,people.get('city'))

            bdate = people.get('bdate')
            if bdate is None:
                continue
            assert isinstance(bdate,str)
            if bdate.count('.') is 2:
                auxMath.addToDict(berd,bdate[-4:])
            if 'universities' in people and len(people.get('universities')) > 0:
                t = people.get('universities')[0]
                auxMath.addToDict(univers,people.get('universities')[0].get('name'))
        #обработка частотных ловарей. Выделение наиболее встречаемых
        topbdate = auxMath.findTopFreq(berd)

        topcity = auxMath.findTopFreq(city)
        for i,v in enumerate(topcity):
            t = self.evalWithCache('database.getCitiesById(city_ids=%s)'%str(topcity[i][0]))
            if len(t) is 0:
                t = "Не известно"
            else:
                t = t[0]['name']
            topcity[i] = list(v)
            topcity[i][0] = t

        toptuniversity = auxMath.findTopFreq(univers)

        if service is not None:
            return (topbdate,reportBirthDay, topcity)
        reportBirthDay = auxMath.birthPeriodReport(topbdate)
        reportCity = auxMath.cityReport(topcity)
        reportUniversity = auxMath.universitiesReport(toptuniversity,friendsNumber)
        return (topbdate,reportBirthDay, topcity,reportCity, toptuniversity,reportUniversity)

    def test(self, id):
        x = self.evalWithCache("friends.get(user_id=%s,order='name', fields='%s')"%(str(id),self.researchFields))
        pprint(x)




class socialAnalyze(analytic):
    def __init__(self,vk,logtxt,logger):
        self.vk, self.logtxt, self.logger = vk,logtxt,logger

    #беру некоторый user id в Вконтакте например, http://vk.com/id200000000
    #в цикле пока переменную успешных опросов не достигнет 1000:
    #- смотрим указана на странице полная дата рождения, учебное заведение и город и открыты ли более 30 друзей
    #- если да то делаем анализ и сравниваем с данными из анкеты + записываем результаты в лог
    #- увеличиваем переменную успешных анализов на 1

    def analyzeManyPeople(self):
        id = 200000000
        successProfile = 0
        neededOpenFriends = 30

        while True:
            analyzedMan = self.mainResearch(id,service=True)
            realMan = self.usersGet(id,self.researchFields)
            print(realMan)
            print(analyzedMan)
            break




#нужен универсальный обработчик случаев отсутсвия инфы:
#когда не чего не вернулось, когда вернулся 0
class mainController(object):
    def __init__(self,vk,tw=None):
        self.vk=vk
        self.tw=tw

    def vkApiInterpreter(self,beautifulOut=None):
        print ('input you method')
        while True:
            x = input()
            x = self.vk.eval(x)
            if beautifulOut is not None:
                auxMath.beatifulOut(x)
            else:
                print(x)

    def mainResearchInterpreter(self,beautifulOut=None):
        print ('Enter the username(id or shortname) for the report')
        while True:
            x = input()
            x = self.vk.mainResearch(int(x))
            if beautifulOut is not None:
                auxMath.beatifulOut(x)
            else:
                print(x)


    def test1(self):
        print(self.vk.getServerTime())
        print(self.vk.friends.get(fields='uid, first_name, last_name, nickname, sex, bdate',uid='21229916'))
        #vk = vkontakte.API(token=getCredent('credentials.txt'))
        #print "Hello vk API , server time is ",vk.getServerTime()
        #print unicode(vk.users.get(uids=146040808))
        #reader.read(vk.users.get(uids=233945283,fields='sex'))
        #log.responseLog(vk.usersGet(vk.eval(vk.t1)))
        #print(vk.researchFields2.split(','))
        #print (vk.getServerTime())

def main():
    log = logger()
    vk = analytic(getCredent('credentials.txt'))
    tw = textViewer(vk)
    mainClass = mainController(vk,tw)
    #research = vk.mainResearch(226723565)
    #print(research[2])
    #print(vk.mainResearch(72858365)[2])
    #print(vk.mainResearch(150798434)[2]) #78340794 182541327

    #x = vk.social.analyzeManyPeople()
    #x = vk.social.analyzeManyPeople()

    x = vk.mainResearch(5859210)
    print(x)
    auxMath.beatifulOut(x)

    #vk.test(3870390)
    #mainClass.vkApiInterpreter()
    #mainClass.mainResearchInterpreter()
    return 0

if __name__ == '__main__':
    try:
        main()
    except EOFError:
        exit(0)


