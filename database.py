# -*- coding: utf-8  -*-
"""
Script para consultas ao banco de dados
"""
import os, oursql
from datetime import date

def template(page, args=[]):
    functions = {u'Usuário': 'EditsAndRights(*args)',
                 u'Patrulhamento_de_IPs': 'ippatrol()'}
    if page in functions:
        return eval(functions[page])
    else:
        return {}

def conn(wiki):
    try:
        connection = oursql.connect(db=wiki + '_p', host=wiki + '.labsdb', read_default_file=os.path.expanduser('~/replica.my.cnf'))
        return connection.cursor()
    except:
        return False

def EditsAndRights(user):
    """
    Consulta as edições de usuários em todas os projetos lusófonos
    """
    # 'nome da wiki no banco de dados': (tempo-voto, edições-voto, tempo-administrador, edições-administrador, outro-nome, outro-tempo, outro-edições)
    ptwikis = {'ptwiki': (90, 300, 182, 2000, 'eliminador', 182, 1000),
               'ptwikibooks': (30, 50),
               'ptwikiversity': (45, 0),
               'ptwiktionary': (30, 200, 30, 100),
               'ptwikinews': (30, 50),
               'ptwikiquote': (30, 100),
               'ptwikisource': (45, 100),
               'ptwikivoyage': None}
    groups = {'autoreviewer': 'autorrevisor', 'rollbacker': 'reversor', 'bureaucrat': 'burocrata', 'checkuser': 'verificador' ,'oversight': 'supervisor',
              'reviewer': 'revisor', 'import': 'importador'}
    response = {}
    user = user.replace(u'_', u' ')
    for wiki in ptwikis:
        c = conn(wiki)
        if not c:
            response[wiki] = {'time': u'Erro', 'total': u'?', 'main': u'?', 'created': u'?', 'vote': u'', 'sysop': u'', 'others': u''}
            continue
        #Consulta edições totais, páginas criadas e primeira edição, separando em domínio principal (main) e outros domínios (others)
        c.execute('''SELECT
 (CASE page_namespace WHEN 0 THEN "main" ELSE "others" END) AS namespace,
 COUNT(*),
 SUM(page_is_new),
 MIN(rev_timestamp)
 FROM revision_userindex
 FULL JOIN page
 ON page_id = rev_page
 WHERE rev_user_text = ?
 GROUP BY namespace''', (user,))
        r = c.fetchall()
        if not r:
            response[wiki] = {'time': u'Nunca editou', 'total': u'0', 'main': u'0', 'created': u'0', 'vote': u'—', 'sysop': u'—', 'others': u'—'}
            continue
        c.execute('SELECT ug_group FROM user LEFT JOIN user_groups ON user_id = ug_user WHERE user_name = ?', (user,))
        g = c.fetchall()
        g = g and [i in groups and groups[i] or i for i in map(lambda i:i[0], g) if i] or []
        # Tempo desde a primeira edição
        t = len(r) == 2 and min(r[0][3], r[1][3]) or r[0][3]
        days = (date.today() - date(int(t[0:4]), int(t[4:6]), int(t[6:8]))).days
        wikitime = u'{}/{}/{}<br />{}'.format(t[6:8], t[4:6], t[0:4], days >= 365 and (days/365 > 1 and str(days/365) + ' anos' or '1 ano')  or
                   days == 1 and '1 dia' or str(days) + ' dias')
        # Edições totais
        total = len(r) == 2 and r[0][1] + r[1][1] or r[0][1]
        # Edições e páginas criadas no domínio principal
        main, created = r[0][0] == u'main' and r[0][1:3] or len(r) == 2 and r[1][1:3] or [0,0]
        # Direito ao voto
        vote = ptwikis[wiki] and (days >= ptwikis[wiki][0] and (main >= ptwikis[wiki][1] and u'<span style="color:#080"><b>Sim</b></span>' or
               u'<span style="color:#800">Não</span><br/><small>menos de {} edições</small>'.format(ptwikis[wiki][1])) or
               u'<span style="color:#800">Não</span><br/><small>menos de {} dias{}</small>'.format(ptwikis[wiki][0],
               main < ptwikis[wiki][1] and u' e de {} edições'.format(ptwikis[wiki][1]))) or u'—'
        # Administrador
        sysop = 'sysop' in g and u'<span style="color:#080"><b>É administrador</b></span>' or ptwikis[wiki] and len(ptwikis[wiki]) > 2 and (
                days >= ptwikis[wiki][2] and (main >= ptwikis[wiki][3] and u'Pode candidatar-se' or
                u'<span style="color:#800">Não pode</span><br/><small>menos de {} edições</small>'.format(ptwikis[wiki][3])) or
                u'<span style="color:#800">Não pode</span><br/><small>menos de {} dias{}</small>'.format(ptwikis[wiki][2],
                main < ptwikis[wiki][1] and u' e de {} edições'.format(ptwikis[wiki][1]))) or u'—'
        # Outros direitos
        others = ptwikis[wiki] and len(ptwikis[wiki]) == 7 and 'sysop' not in g and ptwikis[wiki][4] not in g and (days >= ptwikis[wiki][2] and
                (main >= ptwikis[wiki][3] and u'Pode candidatar-se a {}'.format(ptwikis[wiki][4]) or
                u'<span style="color:#800">Não pode candidatar-se a {}</span><br/><small>menos de {} edições</small>'.format(ptwikis[wiki][4], ptwikis[wiki][6])) or
                u'<span style="color:#800">Não pode candidatar-se a {}</span><br/><small>menos de {} dias{}</small>'.format(ptwikis[wiki][4], ptwikis[wiki][5],
                total < ptwikis[wiki][1] and u' e de {} edições'.format(ptwikis[wiki][6]))) or None
        others = g and u'<br />'.join((others and [others] or []) + [u'<span style="color:#080"><b>É {}</b></span>'.format(i) for i in g if i != 'sysop']) or others or u'—'
        response[wiki] = {'time': wikitime, 'total': str(total), 'main': str(main), 'created': str(created), 'vote': vote, 'sysop': sysop, 'others': others}
    variables = dict([('{}_{}'.format(item, wiki), response[wiki][item])for wiki in response for item in response[wiki]])
    variables['user'] = user
    return variables

def ippatrol():
    c = conn('ptwiki')
    if c:
        c.execute('''SELECT
 SUBSTR(rc_timestamp, 1, 10) AS HORA,
 COUNT(*),
 SUM(rc_patrolled)
 FROM recentchanges
 WHERE rc_namespace = 0 AND rc_user = 0 AND rc_type != 5
 GROUP BY HORA
 ORDER BY rc_id DESC
 LIMIT 168''')
        r = c.fetchall()
        r = {'iphquery': ','.join([(x in r[6::6] and '\n[{},{},{}]' or '[{},{},{}]').format(*x) for x in r])}
    else:
        r = {'iphquery': '''[2013070915,146,13],[2013070914,159,31],[2013070913,124,35],[2013070912,103,16],[2013070911,75,20],[2013070910,46,16],
[2013070909,20,1],[2013070908,40,3],[2013070907,21,4],[2013070906,57,3],[2013070905,33,1],[2013070904,63,9],
[2013070903,119,21],[2013070902,118,24],[2013070901,170,38],[2013070900,198,49],[2013070823,184,69],[2013070822,207,74],
[2013070821,180,38],[2013070820,123,36],[2013070819,207,44],[2013070818,201,60],[2013070817,225,60],[2013070816,187,24],
[2013070815,148,25],[2013070814,131,27],[2013070813,116,16],[2013070812,72,7],[2013070811,52,8],[2013070810,45,1],
[2013070809,25,6],[2013070808,39,11],[2013070807,27,3],[2013070806,23,4],[2013070805,37,4],[2013070804,57,13],
[2013070803,69,33],[2013070802,84,10],[2013070801,172,38],[2013070800,187,36],[2013070723,145,53],[2013070722,152,32],
[2013070721,144,32],[2013070720,143,33],[2013070719,129,48],[2013070718,115,22],[2013070717,161,24],[2013070716,137,42],
[2013070715,157,39],[2013070714,98,31],[2013070713,58,17],[2013070712,32,6],[2013070711,45,4],[2013070710,30,2],
[2013070709,25,0],[2013070708,12,2],[2013070707,20,3],[2013070706,27,4],[2013070705,42,5],[2013070704,123,32],
[2013070703,193,31],[2013070702,131,21],[2013070701,126,24],[2013070700,118,26],[2013070623,140,25],[2013070622,185,40],
[2013070621,146,46],[2013070620,162,20],[2013070619,167,38],[2013070618,177,40],[2013070617,129,51],[2013070616,121,27],
[2013070615,135,32],[2013070614,111,36],[2013070613,72,14],[2013070612,41,7],[2013070611,21,2],[2013070610,25,2],
[2013070609,28,5],[2013070608,23,1],[2013070607,39,13],[2013070606,44,10],[2013070605,53,10],[2013070604,35,6],
[2013070603,64,25],[2013070602,68,31],[2013070601,97,29],[2013070600,123,29],[2013070523,125,32],[2013070522,119,38],
[2013070521,95,38],[2013070520,116,37],[2013070519,127,39],[2013070518,105,23],[2013070517,193,55],[2013070516,145,52]'''}
    return r