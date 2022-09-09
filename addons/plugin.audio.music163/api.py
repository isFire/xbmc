# -*- coding:utf-8 -*-
import json
import os
import sys
import platform
import time
import requests
from encrypt import encrypted_request
from xbmcswift2 import Plugin, xbmcgui, xbmc, xbmcaddon,xbmcplugin
import re

DEFAULT_TIMEOUT = 10

BASE_URL = "https://music.163.com"

class NetEase(object):
    def __init__(self,account):
        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip,deflate,sdch",
            "Accept-Language": "zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "music.163.com",
            "Referer": "http://music.163.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        }
        self.account = account
        self.session = requests.Session()
        self.enable_proxy = False
        if xbmcplugin.getSetting(int(sys.argv[1]),'enable_proxy') == 'true':
            self.enable_proxy = True
            proxy = xbmcplugin.getSetting(int(sys.argv[1]),'host').strip() + ':' + xbmcplugin.getSetting(int(sys.argv[1]),'port').strip()
            self.proxies = {
                'http':'http://' + proxy,
                'https':'https://' + proxy,
            }
        requests.utils.add_dict_to_cookiejar(self.session.cookies, {'MUSIC_U':account['MUSIC_U'],'__csrf':account['__csrf'],'__remember_me':account['__remember_me'],'os':'pc'}) 

    def _raw_request(self, method, endpoint, data=None):
        if method == "GET":
            if not self.enable_proxy:
                resp = self.session.get(
                    endpoint, params=data, headers=self.header, timeout=DEFAULT_TIMEOUT
                )
            else:
                resp = self.session.get(
                    endpoint, params=data, headers=self.header, timeout=DEFAULT_TIMEOUT, proxies = self.proxies
                )
        elif method == "POST":
            if not self.enable_proxy:
                resp = self.session.post(
                    endpoint, data=data, headers=self.header, timeout=DEFAULT_TIMEOUT
                )
            else:
                resp = self.session.post(
                    endpoint, data=data, headers=self.header, timeout=DEFAULT_TIMEOUT, proxies = self.proxies
                )
        return resp

    # 生成Cookie对象
    def make_cookie(self, name, value):
        return Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain="music.163.com",
            domain_specified=True,
            domain_initial_dot=False,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
        )

    def request(self, method, path, params={}, default={"code": -1}, custom_cookies={'os':'pc'}, return_json=True):
        endpoint = "{}{}".format(BASE_URL, path)
        csrf_token = ""
        for cookie in self.session.cookies:
            if cookie.name == "__csrf":
                csrf_token = cookie.value
                break
        params.update({"csrf_token": csrf_token})
        data = default

        # for key, value in custom_cookies.items():
            # cookie = self.make_cookie(key, value)
            # self.session.cookies.set_cookie(cookie)

        params = encrypted_request(params)
        try:
            resp = self._raw_request(method, endpoint, params)
            if return_json:
                data = resp.json()
            else:
                data = resp.text
        except requests.exceptions.RequestException as e:
            log.error(e)
        except ValueError as e:
            log.error("Path: {}, response: {}".format(path, resp.text[:200]))
        finally:
            return data

    def login(self, username, password):
        if username.isdigit():
            path = "/weapi/login/cellphone"
            params = dict(phone=username, password=password, rememberLogin="true")
        else:
            # magic token for login
            # see https://github.com/Binaryify/NeteaseCloudMusicApi/blob/master/router/login.js#L15
            client_token = (
                "1_jVUMqWEPke0/1/Vu56xCmJpo5vP1grjn_SOVVDzOc78w8OKLVZ2JH7IfkjSXqgfmh"
            )
            path = "/weapi/login"
            params = dict(
                username=username,
                password=password,
                rememberLogin="true",
                clientToken=client_token,
            )
        data = self.request("POST", path, params)
        #保存cookie
        for cookie in self.session.cookies:
            self.account[cookie.name] = cookie.value
        return data

    # 每日签到
    def daily_task(self, is_mobile=True):
        path = "/weapi/point/dailyTask"
        params = dict(type=0 if is_mobile else 1)
        return self.request("POST", path, params)

    # 用户歌单
    def user_playlist(self, uid, offset=0, limit=1000,includeVideo=True):
        path = "/weapi/user/playlist"
        params = dict(uid=uid, offset=offset, limit=limit, includeVideo=includeVideo,csrf_token="")
        return self.request("POST", path, params).get("playlist", [])
        # specialType:5 喜欢的歌曲; 200 视频歌单; 0 普通歌单

    # 每日推荐歌单
    def recommend_resource(self):
        path = "/weapi/v1/discovery/recommend/resource"
        return self.request("POST", path).get("recommend", [])

    # 每日推荐歌曲
    def recommend_playlist(self, total=True, offset=0, limit=20):
        path = "/weapi/v3/discovery/recommend/songs"  # NOQA
        params = dict(total=total, offset=offset, limit=limit, csrf_token="")
        return self.request("POST", path, params).get('data',{}).get('dailySongs',[])

    #获取历史日推可用日期
    def history_recommend_recent(self):
        path = "/weapi/discovery/recommend/songs/history/recent"
        return self.request("POST", path).get('data', {}).get('dates', [])     
        # {'dates': ['2020-10-31', '2020-10-27', '2020-10-26', '2020-10-23', '2020-10-22'], 'purchaseUrl': 'https://music.163.com/prime/m/purchase?luxury=1&situation=dailyHistory', 'description': '您已尊享查看60天内近5次历史日推的特权', 'noHistoryMessage': '黑胶VIP可查看近期5次历史记录，明天再来就会有哦'}

    #获取历史日推
    def history_recommend_detail(self,date=''):
        path = "/weapi/discovery/recommend/songs/history/detail"
        params = dict(date=date)
        return self.request("POST", path, params).get('data',{}).get('songs',[])       

    # 私人FM
    def personal_fm(self):
        path = "/weapi/v1/radio/get"
        return self.request("POST", path).get("data", [])

    # like
    def fm_like(self, songid, like=True, time=25, alg="itembased"):
        path = "/weapi/radio/like"
        params = dict(
            alg=alg, trackId=songid, like="true" if like else "false", time=time
        )
        return self.request("POST", path, params)["code"] == 200

    # FM trash
    def fm_trash(self, songid, time=25, alg="RT"):
        path = "/weapi/radio/trash/add"
        params = dict(songId=songid, alg=alg, time=time)
        return self.request("POST", path, params)["code"] == 200

    # 搜索单曲(1)，歌手(100)，专辑(10)，歌单(1000)，用户(1002)，歌词(1006)，主播电台(1009)，MV(1004)，视频(1014)，综合(1018) *(type)*
    def search(self, keywords, stype=1, offset=0, total="true", limit=100):
        path = "/weapi/search/get"
        params = dict(s=keywords, type=stype, offset=offset, total=total, limit=limit)
        return self.request("POST", path, params).get("result", {})

    # 新碟上架
    def new_albums(self, offset=0, limit=50):
        path = "/weapi/album/new"
        params = dict(area="ALL", offset=offset, total=True, limit=limit)
        return self.request("POST", path, params)#.get("albums", [])

    # 歌单（网友精选碟） hot||new http://music.163.com/#/discover/playlist/
    def top_playlists(self, category="全部", order="hot", offset=0, limit=50):
        path = "/weapi/playlist/list"
        params = dict(
            cat=category, order=order, offset=offset, total="true", limit=limit
        )
        return self.request("POST", path, params).get("playlists", [])

    def playlist_catelogs(self):
        path = "/weapi/playlist/catalogue"
        return self.request("POST", path)

    # # 歌单详情
    # def playlist_detail(self, playlist_id):
        # path = "/weapi/v3/playlist/detail"
        # params = dict(id=playlist_id, total="true", limit=1000, n=1000, offest=0)
        # # cookie添加os字段
        # custom_cookies = dict(os=platform.system())
        # return (
            # self.request("POST", path, params, {"code": -1}, custom_cookies)
            # .get("playlist", {})
            # .get("tracks", [])
        # )

    # 歌单详情
    def playlist_detail(self, id,shareUserId=0):
        path = "/weapi/v6/playlist/detail"
        params = dict(id=id, t=int(time.time()),n=1000, s=5,shareUserId=shareUserId)
        # cookie添加os字段
        # custom_cookies = dict(os=platform.system())
        return (
            # self.request("POST", path, params, {"code": -1}, custom_cookies)
            self.request("POST", path, params, {"code": -1})
            #.get("playlist", {})
            #.get("tracks", [])
        )

    # 热门歌手 http://music.163.com/#/discover/artist/
    def top_artists(self, offset=0, limit=100, total=True):
        path = "/weapi/artist/top"
        params = dict(offset=offset, total=total, limit=limit)
        return self.request("POST", path, params).get("artists", [])

    # 歌手单曲
    def artists(self, artist_id):
        path = "/weapi/v1/artist/{}".format(artist_id)
        return self.request("POST", path).get("hotSongs", [])

    def artist_album(self, artist_id, offset=0, limit=50):
        path = "/weapi/artist/albums/{}".format(artist_id)
        params = dict(offset=offset, total=True, limit=limit)
        return self.request("POST", path, params)#.get("hotAlbums", [])

    # album id --> song id set
    def album(self, album_id):
        path = "/weapi/v1/album/{}".format(album_id)
        return self.request("POST", path)#.get("songs", [])

    def song_comments(self, music_id, offset=0, total="false", limit=100):
        path = "/weapi/v1/resource/comments/R_SO_4_{}/".format(music_id)
        params = dict(rid=music_id, offset=offset, total=total, limit=limit)
        return self.request("POST", path, params)

    # song ids --> song urls ( details )
    def songs_detail(self, ids):
        path = "/weapi/v3/song/detail"
        params = dict(c=json.dumps([{"id": _id} for _id in ids]), ids=json.dumps(ids))
        return self.request("POST", path, params)#.get("songs", [])

    def songs_url(self, ids, bitrate):
        path = "/weapi/song/enhance/player/url"
        params = dict(ids=ids, br=bitrate)
        return self.request("POST", path, params).get("data", [])

    # lyric http://music.163.com/api/song/lyric?os=osx&id= &lv=-1&kv=-1&tv=-1
    def song_lyric(self, music_id):
        path = "/weapi/song/lyric"
        params = dict(os="osx", id=music_id, lv=-1, kv=-1, tv=-1)
        lyric = self.request("POST", path, params).get("lrc", {}).get("lyric", [])
        # if not lyric:
        #     return []
        # else:
        #     return lyric.split("\n")
        return lyric

    def song_tlyric(self, music_id):
        path = "/weapi/song/lyric"
        params = dict(os="osx", id=music_id, lv=-1, kv=-1, tv=-1)
        lyric = self.request("POST", path, params).get("tlyric", {}).get("lyric", [])
        if not lyric:
            return []
        else:
            return lyric.split("\n")

    # 今日最热（0）, 本周最热（10），历史最热（20），最新节目（30）
    def djchannels(self, offset=0, limit=50):
        path = "/weapi/djradio/hot/v1"
        params = dict(limit=limit, offset=offset)
        channels = self.request("POST", path, params).get("djRadios", [])
        return channels

    def dj_program(self, radio_id, asc=False, offset=0, limit=50):
        path = "/weapi/dj/program/byradio"
        params = dict(asc=asc, radioId=radio_id, offset=offset, limit=limit)
        return self.request("POST", path, params)

    def dj_sublist(self, offset=0, limit=50):
        path = "/weapi/djradio/get/subed"
        params = dict(offset=offset, limit=limit,total=True)
        return self.request("POST", path, params)         
        
    def dj_detail(self,id):
        path="/weapi/dj/program/detail"
        params=dict(id=id)
        return self.request("POST", path,params)           
               
    # 打卡
    def daka(self, id, sourceId=0, time=240):
        path = "/weapi/feedback/weblog"        
        params = {'logs': json.dumps([{
            'action': 'play',
            'json': {
                    "download": 0,
                    "end": 'playend',
                    "id": id,
                    "sourceId": sourceId,
                    "time": time,
                    "type": 'song',
                    "wifi": 0,
                    }
        }])}
        return self.request("POST", path, params)
        
    # 是否登录
    def login_status(self):
        path = ''
        html = self.request("GET", path,return_json=False)
        return 'GUser' in html and 'GUser={}' not in html
        
    # 获取用户id
    def get_uid(self):
        path = ''
        html = self.request("GET", path,return_json=False)
        uid = re.findall(r'GUser=\{userId:(.*?),',html)[0]
        return uid
    # 云盘歌曲   
    def cloud_songlist(self, offset=0, limit=50):
        path = "/weapi/v1/cloud/get"
        params = dict(offset=offset, limit=limit, csrf_token="")       
        return self.request("POST", path, params)#.get("data", [])
        
    # 歌手信息
    def artist_info(self, artist_id):
        path = "/weapi/v1/artist/{}".format(artist_id)
        return self.request("POST", path).get("artist", {})

    def artist_songs(self, id, limit=50, offset=0):
        path = "/weapi/v1/artist/songs"
        params = dict(id=id,limit=limit,offset=offset,private_cloud=True,work_type=1,order='hot')
        return self.request("POST", path, params)

    # # 歌手热门歌曲
    # def artist_topsong(self, artist_id):
        # path = "/api/artist/top/song"
        # params = dict(id = artist_id)
        # return self.request("POST", path, params)     
    #获取MV url
    def mv_url(self, id):
        path = "/weapi/song/enhance/play/mv/url"
        params = dict(id=id, r=1080)
        return self.request("POST", path, params).get("data", {})          
    #收藏的歌手
    def artist_sublist(self, offset=0,limit=50,total=True):
        path = "/weapi/artist/sublist"
        params = dict(offset=offset,limit=limit,total=total)
        return self.request("POST", path, params).get("data", [])  
    #收藏的专辑
    def album_sublist(self, offset=0,limit=50,total=True):
        path = "/weapi/album/sublist"
        params = dict(offset=offset,limit=limit,total=total)
        return self.request("POST", path, params).get("data", [])         
    #收藏的视频
    def video_sublist(self, offset=0,limit=50,total=True):
        path = "/weapi/cloudvideo/allvideo/sublist"
        params = dict(offset=offset,limit=limit,total=total)
        return self.request("POST", path, params).get("data", [])       
    #获取视频url
    def video_url(self, id, resolution=1080):
        path = "/weapi/cloudvideo/playurl"
        params = dict(ids='["' + id + '"]',resolution = resolution)
        return self.request("POST", path, params).get("urls", [])         
   #我的数字专辑
    def digitalAlbum_purchased(self, offset=0,limit=50,total=True):
        path = "/api/digitalAlbum/purchased"
        params = dict(offset=offset,limit=limit,total=total)
        return self.request("POST", path, params).get("paidAlbums", [])
    # 已购单曲
    def single_purchased(self, offset=0,limit=1000,total=True):
        path = "/weapi/single/mybought/song/list"
        # path = "/weapi/member/song/singledownlist"
        params = dict(offset=offset,limit=limit)
        return self.request("POST", path, params)                 
    #排行榜
    def toplists(self):
        path = "/api/toplist"
        return self.request("POST", path).get("list", [])         
    #新歌速递 全部:0 华语:7 欧美:96 日本:8 韩国:16
    def new_songs(self, areaId=0, total=True):
        path = "/weapi/v1/discovery/new/songs"
        params = dict(areaId=areaId, total=total)
        return self.request("POST", path, params).get("data", [])      
    #歌手MV
    def artist_mvs(self, id, offset=0,limit=50,total=True):
        path = "/weapi/artist/mvs"
        params = dict(artistId=id,offset=offset,limit=limit,total=total)
        return self.request("POST", path, params).get("mvs", [])           
    #相似歌手
    def similar_artist(self, artistid):
        path = "/weapi/discovery/simiArtist"
        params = dict(artistid=artistid)
        return self.request("POST", path, params).get("artists", [])         
    #用户信息
    def user_detail(self, id):
        path = "/weapi/v1/user/detail/{}".format(id)
        return self.request("POST", path)          
    #关注用户
    def user_follow(self, id):
        path = "/weapi/user/follow/{}".format(id)
        return self.request("POST", path) 
    #取消关注用户
    def user_delfollow(self, id):
        path = "/weapi/user/delfollow/{}".format(id)
        return self.request("POST", path)          
    #用户关注列表
    def user_getfollows(self, id, offset=0,limit=50,order=True):
        path = "/weapi/user/getfollows/{}".format(id)
        params = dict(offset=offset,limit=limit,order=order)
        return self.request("POST", path, params)#.get("follow", [])          
    # #用户粉丝列表
    # def user_getfolloweds(self, id, time=-1,limit=50):
    #     path = "/weapi/user/getfolloweds/{}".format(id)
    #     params = dict(time=time,limit=limit)
    #     return self.request("POST", path, params)#.get("followeds", [])         
    # 用户粉丝列表
    def user_getfolloweds(self, userId, offset=0,limit=30):
        path = "/weapi/user/getfolloweds"
        params = dict(userId=userId,offset=offset,limit=limit,getcounts=True)
        return self.request("POST", path, params)#.get("followeds", [])     
    #听歌排行 type: 0 全部时间 1最近一周
    def play_record(self, uid, type=0):
        path = "/weapi/v1/play/record"
        params = dict(uid=uid,type=type)
        return self.request("POST", path, params)#.get("allData", [])         
    #MV排行榜 area: 地区,可选值为内地,港台,欧美,日本,韩国,不填则为全部
    def top_mv(self, area='', limit=50, offset=0, total=True):
        path = "/weapi/mv/toplist"
        params = dict(area=area,limit=limit,offset=offset,total=total)
        return self.request("POST", path, params)#.get("data", [])          

    # ----MLOG----
    # MLOG广场 channelId: 1001视频,4演唱,2音乐安利,3演奏,1002MV,8001生活,6001舞蹈,3001混剪
    def mlog_socialsquare(self,channelId=1001,pagenum=0):
        path="/weapi/socialsquare/v1/get"
        params=dict(pagenum=pagenum,netstate=1,first=(str(pagenum)=='0'),channelId=channelId,dailyHot=(str(pagenum)=='0'))
        return self.request("POST", path, params) 

    # 推荐MLOG
    def mlog_rcmd(self,id,limit=3,type=1,rcmdType=0,lastRcmdResType=1,lastRcmdResId='',viewCount=1,channelId=1001):
        path="/weapi/mlog/rcmd/v3"
        params=dict(id=id,limit=limit,type=type,rcmdType=rcmdType,lastRcmdResType=lastRcmdResType,extInfo=dict(channelId=channelId),viewCount=viewCount)
        return self.request("POST", path, params)   

    # MLOG详情
    def mlog_detail(self,id,resolution=720,type=1):
        path="/weapi/mlog/detail/v1"
        params=dict(id=id,resolution=resolution,type=type)
        return self.request("POST", path, params)           

    # 创建歌单 privacy:0 为普通歌单，10 为隐私歌单；type:NORMAL|VIDEO
    def playlist_create(self, name, privacy=0, ptype='NORMAL'):
        path = "/weapi/playlist/create"
        params = dict(name=name,privacy=privacy,type=ptype)
        return self.request("POST", path, params) 
    
    # 删除歌单
    def playlist_delete(self, ids):
        path = "/weapi/playlist/remove"        
        params = dict(ids=ids)
        return self.request("POST", path, params)
        # {'code': 200}      

    # 添加MV到视频歌单中
    def playlist_add(self, pid, ids):
        path = "/weapi/playlist/track/add"
        ids = [{'type':3,'id':song_id} for song_id in ids]
        params = {'id':pid,'tracks': json.dumps(ids)}
        return self.request("POST", path, params)    

    # 添加/删除单曲到歌单
    # op:'add'|'del'
    def playlist_tracks(self, pid, ids,op='add'):
        path = "/weapi/playlist/manipulate/tracks"        
        params = {'op':op,'pid':pid,'trackIds': json.dumps(ids),'imme':'true'}
        result = self.request("POST", path, params)  
        # 可以收藏收费歌曲和下架歌曲            
        if result['code'] != 200:
            ids.extend(ids)
            params = {'op':op,'pid':pid,'trackIds': json.dumps(ids),'imme':'true'}
            result = self.request("POST", path, params)            
        return result
        # 401 下架歌曲无法收藏 | 512 付费歌曲无法收藏

    # 收藏歌单
    def playlist_subscribe(self,id):
        path="/weapi/playlist/subscribe"
        params=dict(id=id)
        return self.request("POST", path,params)    
        # {'code': 200}
        # {'code': 501} 已经收藏过了  

    # 取消收藏歌单
    def playlist_unsubscribe(self,id):
        path="/weapi/playlist/unsubscribe"
        params=dict(id=id)
        return self.request("POST", path,params)  
        # {'code': 200} 