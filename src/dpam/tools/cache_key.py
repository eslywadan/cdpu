import sys
from collections import OrderedDict

def get_cache_key(path):
    return 'ph_' + clean_qs2(path)


#1.從query string拿掉可以省略的query條件，例如recipe=%2A(recipe=*)
#2.month條件移到最後
#3.以OrderedDict實作
def clean_qs2(path):
    qm_pos = path.find("?")
    if qm_pos < 0: return path

    #取得query string並轉為query條件組成的OrderedDict
    q_od = OrderedDict()
    qs = path[qm_pos + 1 : ]
    for q in qs.split('&'):
        qpair = q.split("=")
        if len(qpair) == 2 and qpair[1] != "%2A" and qpair[1] != "*": #不取*結尾的query條件
            q_od[qpair[0]] = qpair[1]

    #month條件移到最後
    if 'month' in q_od:
        q_od.move_to_end("month")

    #組回處理好的query string
    if len(q_od) > 0:
        qs = '&'.join(f'{k}={v}' for k,v in q_od.items())
        new_path = path[0 : qm_pos + 1] + qs
    else:
        new_path = path[0 : qm_pos]

    return new_path



#1.從query string拿掉可以省略的query條件，例如recipe=%2A(recipe=*)
#2.month條件移到最後
def clean_query_string(path):
    qm_pos = path.find("?")
    if qm_pos < 0: return path

    #取得query string並轉為query條件組成的list
    qs = path[qm_pos + 1 : ]
    qlist = qs.split('&')

    #拿掉*結尾的query條件
    qlist = [q for q in qlist if q[-3:]!="%2A" and q[-1]!="*"]

    #month條件移到最後
    month_q = None
    for q in qlist:
        if q.startswith('month='): month_q = q

    if month_q is not None and month_q != qlist[-1]:
        qlist.remove(month_q)
        qlist.append(month_q)

    #組回處理好的query string
    if len(qlist) == 0 or len(qlist) == 1 and qlist[0] == '':
        new_path = path[0 : qm_pos]
    else:
        new_path = path[0 : qm_pos + 1] + "&".join(qlist)
    
    return new_path


if __name__ == "__main__":
    path = sys.argv[1]
    method = sys.argv[2]
    new_path = clean_query_string(path) if method == '1' else clean_qs2(path)
    print(new_path)
