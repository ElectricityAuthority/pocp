import pandas as pd
import mechanize
from datetime import datetime, timedelta
from io import StringIO
import pandas.io.sql as sql
import argparse
import numpy as np
import EAtools as ea
import json

###############################################################################
#Setup command line option and argument parsing
###############################################################################

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--pocp_host', action="store", dest='pocp_host',
                    default='http://pocp.redspider.co.nz/')
parser.add_argument('--pocp_user', action="store", dest='pocp_user',
                    default='david.hume')
parser.add_argument('--pocp_pass', action="store", dest='pocp_pass')
parser.add_argument('--dw_user', action="store", dest='dw_user',
                    default='ECOM\humed')
parser.add_argument('--dw_pass', action="store", dest='dw_pass')
parser.add_argument('--pocp_path', action="store", dest='pocp_path',
                    default='/home/dave/python/pocp/')

IPy_notebook = False

if IPy_notebook:
    ea.set_options()

    class cmd_line():
        def __init__(self, pocp_host, pocp_user, pocp_pass, dw_user, dw_pass, pocp_path):
            self.pocp_host = pocp_host
            self.pocp_user = pocp_user
            self.pocp_pass = pocp_pass
            self.dw_user = dw_user
            self.dw_pass = dw_pass
            self.pocp_path = pocp_path
else:
    cmd_line = parser.parse_args()

###############################################################################
#  Download the the last year of POCP database, append to historical data->csv
###############################################################################


class POCP(object):
    '''This is the POCP class'''
    def __init__(self, cmd_line, start_time=None, end_time=None):
        self.cmd_line = cmd_line
        self.start_time = start_time
        self.end_time = end_time
        self.update_time = None
        self.currDL = None
        self.con = ea.DW_connect(DSN='DWMarketData_test',
                                 user=self.cmd_line.dw_user,
                                 passwd=self.cmd_line.dw_pass)
        self.addImaps = {'ANC': 'NI', 'KAG': 'NI', 'KTW': 'NI', 'NAP': 'NI',
                         'PRI': 'NI', 'TAA': 'NI', 'TAP': 'NI', 'TUK': 'NI',
                         'WHL': 'SI', 'WWD': 'NI', 'THI': 'NI', 'n/a': np.nan}
        self.addGmaps = {'ABY': 'Hydro', 'ANC': 'Thermal', 'BLN': 'Hydro',
                         'BPE': 'Wind', 'BRB': 'Thermal', 'CST': 'Hydro',
                         'DOB': 'Hydro', 'HAM': 'Thermal', 'HKK': 'Hydro',
                         'HUI': 'Hydro', 'HWB': 'Wind', 'KAG': 'Geothermal',
                         'KOE': 'Geothermal', 'KTW': 'Hydro', 'KUM': 'Hydro',
                         'LTN': 'Wind', 'NSY': 'Hydro', 'PRI': 'Hydro',
                         'TAA': 'Geothermal', 'TAP': 'Wind', 'TGA': 'Hydro',
                         'TUK': 'Wind', 'RDF': 'Hydro', 'WHL': 'Wind',
                         'THI': 'Geothermal', 'n/a': np.nan}

    #mappings
    def generation_type_map(self):
        gens = sql.read_frame("Select * from com.MAP_Generating_plant", self.con)
        gens = gens[gens['Connection_Type'] == 'G']
        GT = gens.set_index('POC').Generation_Type.reset_index()
        GT['POC'] = GT.POC.map(lambda x: x[0: 3])
        GT = GT.drop_duplicates().set_index('POC').Generation_Type
        GT.ix['KAW'] = 'Geothermal'
        self.GT = GT.to_dict()
        self.GT = dict(self.GT.items() + self.addGmaps.items())

    def island_map(self):
        island = sql.read_frame("Select * from com.MAP_PNode_to_POC_and_island", self.con)
        island_map = island.set_index('POC').Island
        island_map.index = island_map.index.map(lambda x: x[0: 3])
        self.island_map = island_map.reset_index().drop_duplicates().set_index('index').Island.to_dict()
        self.island_map = dict(self.island_map.items() + self.addImaps.items())

    def mappings(self, df):
        self.island_map()
        self.generation_type_map()
        df['Generation type'] = df.GIP.map(lambda x: self.GT[x])
        df['Island'] = df.GIP.map(lambda x: self.island_map[x])
        return df

    def dt_convert(self, x):
        if isinstance(x, basestring):
            date = x.split(' ')[0].split('-')
            time = x.split(' ')[1].split(':')
            return datetime(int(date[0]), int(date[1]), int(date[2]),
                            int(time[0]), int(time[1]), int(time[2]))
        else:
            return x

    def set_date_range(self):
        self.update_time = datetime.now()
        if self.start_time is None:
            self.strt = (self.update_time - timedelta(.5 * 365))  # 6 mon<-
            self.start_time = self.strt.strftime('%d/%m/%Y')
        if self.end_time is None:
            self.endt = (self.update_time + timedelta(0.5 * 365))  # ~6 mon->
            self.end_time = self.endt.strftime('%d/%m/%Y')

    def download_pocp(self):  # Note: redspider limit<10000 rows
        def POCP_date_parser(datestr):
            d = datestr.replace('/', ' ').replace(':', ' ').split(' ')
            return datetime(int('20' + d[2]), int(d[1]), int(d[0]), int(d[3]), int(d[4]))

        print 'Getting POCP between ' + self.start_time + ' and ' + self.end_time

        bufferIO = StringIO()

        br = mechanize.Browser(factory=mechanize.RobustFactory())
        br.set_proxies({"http": "172.29.52.38: 8081"})
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)  # Follows refresh 0 but not hangs on refresh > 0
        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv: 1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        br.open(cmd_line.pocp_host)
        br.select_form(nr=0)
        br.submit()  # click I agree
        br.select_form(nr=0)  # login
        br['email'] = cmd_line.pocp_user
        br['password'] = cmd_line.pocp_pass
        br.submit()  # submit user name and password.
        br.select_form(nr=0)  # select form
        br['sview'] = ['excel']  # select "excel" although this is in fact a tab delimited table
        br['start'] = self.start_time  # set start and end times from above
        br['end'] = self.end_time
        br['planning_status_id[]'] = ['1', '2', '3']  # ['1', '2', '3']
        response = br.submit()  # submit the search/download for all POCP data
        bufferIO = StringIO()
        bufferIO.write(unicode(response.read()))
        bufferIO.seek(0)
        self.currDL = pd.read_csv(bufferIO, parse_dates=['Start', 'End', 'Last Modified'],
                                  date_parser=POCP_date_parser, sep='\t', index_col=0)

    def append_pocp(self, pocp):
        P_all = pd.read_csv(self.cmd_line.pocp_path + 'pocp_all.csv', index_col=0)
        self.P = pd.concat([P_all, self.currDL])  # add latest download
        self.P['End'] = self.P.End.map(lambda x: p.dt_convert(x))  # datetimes
        self.P['Start'] = self.P.Start.map(lambda x: p.dt_convert(x))
        self.P['Last Modified'] = self.P['Last Modified'].map(lambda x: p.dt_convert(x))
        self.P = self.P.drop_duplicates()  # drop duplicates
        self.P.to_csv(self.cmd_line.pocp_path + 'pocp_all.csv')  # save updated
        return self.P

    def POCP_logic(self, outage_history=False):
        '''Main POCP grabber, with addition complex logic to try and get what
           we want, with a few assumptions thrown in for good measure...'''
        def POCP_get():
            def get(tdc):
                X = self.P[self.P.Category == tdc]
                # all outages between start and end including those that have been cancelled
                Xbool = ((X['Start'] <= datetime.strptime(p.end_time, '%d/%m/%Y'))
                         & (X['End'] >= datetime.strptime(p.start_time, '%d/%m/%Y')))
                X = X[Xbool]
                X['Duration'] = X.End - X.Start
                if tdc == 'Transmission':
                    del X['MW remaining']
                    del X['MW Loss']
                    del X['MV remaining']
                if tdc == 'Generation':
                    del X['Nature']
                    X['NP_MWh'] = X['Duration'].map(
                        lambda x: x / np.timedelta64(1, 's') / 3600) * X['MW Loss']
                    X = X.sort(columns=['NP_MWh'], ascending=False)
                del X['Category']
                return X
            T = get('Transmission')
            G = get('Generation')
            D = get('Direct Connection')
            if outage_history:
                if not T.empty:
                    T = T.reset_index().set_index(['id', 'Last Modified'],
                                                  drop=False).sortlevel(0)
                if not G.empty:
                    G = G.reset_index().set_index(['id', 'Last Modified'],
                                                  drop=False).sort(columns='MW Loss', ascending=False).sortlevel(0)
                if not D.empty:
                    D = D.reset_index().set_index(['id', 'Last Modified'],
                                                  drop=False).sortlevel(0)
            else:  # this is what you should see in the current pocp database that is now version controlled.
                if not T.empty:
                    #groupby id, return most recent time for that id group
                    IXT = T.reset_index().groupby('id')['Last Modified'].max()
                    T = T.reset_index().set_index(['id', 'Last Modified'],
                                                  drop=False).ix[zip(IXT.to_dict().keys(), IXT.to_dict().values()), :]
                if not G.empty:
                    IXG = G.reset_index().groupby('id')['Last Modified'].max()
                    G = G.reset_index().set_index(['id', 'Last Modified'],
                                                  drop=False).ix[zip(IXG.to_dict().keys(), IXG.to_dict().values()), :]  # select rows
                    G = G.sort(columns='MW Loss', ascending=False)
                if not D.empty:
                    IXD = D.reset_index().groupby('id')['Last Modified'].max()
                    D = D.reset_index().set_index(['id', 'Last Modified']).ix[zip(IXD.to_dict().keys(), IXD.to_dict().values()), :]
            return T, G, D

        def add_caned_after_start(df):
            caned = df[df['Planning Status'] == 'Cancelled']  # cancelled entrys
            caned = caned[caned.index.map(
                          lambda x: x[1]) > caned.Start.tolist()]  # if cancelled after Start time then keep
            confirmed = df[df['Planning Status'] == 'Confirmed']  # confirmed, and
            tentative = df[df['Planning Status'] == 'Tentative']  # tentative
            df = confirmed.append(caned)  # append confirmed outages with those that have been cancelled after the outage window ended
            df = df.append(tentative).sort()  # also append all tentative outages, then sort.
            df['GIP/GXPs'] = df['GIP/GXPs'].map(lambda x: x[0: 3])
            df['GIP/GXPs'][df['GIP/GXPs'] == '#N/'] = 'NAP'
            df = df.rename(columns={'GIP/GXPs': 'GIP'})

            if 'MW Loss' in df.columns:
                df = df[df['MW Loss'] >= 0]
                df = df.ix[:, ['Start', 'End', 'MW Loss', 'Outage Block',
                               'GIP', 'Owner', 'Nature', 'Type', 'Duration',
                               'Planning Status']]
            else:
                df = df.ix[:, ['Start', 'End', 'Outage Block', 'GIP', 'Owner',
                               'Nature', 'Type', 'Duration', 'Planning Status']]

            df = df.fillna(0)
            return df

        T, G, D = POCP_get()  # get all history
        self.G = add_caned_after_start(G)
        self.T = add_caned_after_start(T)

    def today(self, df):
        current_bool = (df['Start'] <= datetime.today()) & (df['End'] >= (datetime.today()))
        df = df[current_bool]
        df = df[df['Planning Status'] == 'Confirmed']
        df = df.drop_duplicates()
        df = df.groupby(level=0).tail(1)  # return the last modified entry...
        return df

    def now(self, df):
        current_bool = (df['Start'] <= datetime.now()) & (df['End'] >= (datetime.now()))
        df = df[current_bool]
        df = df[df['Planning Status'] == 'Confirmed']
        df = df.drop_duplicates()
        df = df.groupby(level=0).tail(1)  # return the last modified entry...
        return df

    def save_metadata(self):
        with open(cmd_line.pocp_path + 'metadata.json', 'w') as outfile:
            json.dump({'updateTime': str(p.update_time.replace(microsecond=0)),
                       'startTime': p.start_time, 'endTime': p.end_time}, outfile)

    def save_generation_data(self):
        p.G.to_csv(cmd_line.pocp_path + 'pocp_data_year.csv')

    def save_transmission_data(self):
        p.T.to_csv(cmd_line.pocp_path + 'pocp_transmission_data_year.csv')

    def main(self):
        outage_history = False
        self.set_date_range()  # set the start and end times
        self.download_pocp()  # download POCP over the data range
        self.append_pocp(self.currDL)  # append current download to the historic POCP data and save.
        self.POCP_logic(outage_history=outage_history)
        self.G = self.mappings(self.G)
        self.Tn = self.now(self.T)
        self.Gn = self.now(self.G)
        self.Tt = self.today(self.T)
        self.Gt = self.today(self.G)
        self.save_metadata()
        self.save_generation_data()
        self.save_transmission_data()

p = POCP(cmd_line)  # the POCP instance
p.main()
