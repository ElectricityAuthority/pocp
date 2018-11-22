#!/usr/bin/python
import pandas as pd
import mechanize
from datetime import datetime, timedelta
from io import StringIO
import argparse
import numpy as np
import json
import re, os
import logging
import logging.handlers

########################################################################
# Setup command line option and argument parsing
########################################################################

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--pocp_host', action="store", dest='pocp_host',
                    default='https://pocp.redspider.co.nz/auth/login')
parser.add_argument('--pocp_user', action="store", dest='pocp_user',
                    default='david.hume@ea.govt.nz')
parser.add_argument('--pocp_pass', action="store", dest='pocp_pass')
parser.add_argument('--pocp_path', action="store", dest='pocp_path',
                    default='/home/humed/monitoring/pocp/')

IPy_notebook = False

if IPy_notebook:
    ea.set_options()

    class cmd_line():
        def __init__(self, pocp_host, pocp_user, pocp_pass,
                     pocp_path):
            self.pocp_host = pocp_host
            self.pocp_user = pocp_user
            self.pocp_pass = pocp_pass
            self.pocp_path = pocp_path
else:
    cmd_line = parser.parse_args()

pocp_path = '/home/humed/monitoring/pocp/'
os.chdir(pocp_path)

#Setup logging
formatter = logging.Formatter('|%(asctime)-6s|%(message)s|', '%Y-%m-%d %H:%M')
consoleLogger = logging.StreamHandler()
consoleLogger.setLevel(logging.INFO)
consoleLogger.setFormatter(formatter)
logging.getLogger('').addHandler(consoleLogger)

fileLogger = logging.handlers.RotatingFileHandler(
    filename=pocp_path + 'pocp.log', maxBytes=1024 * 1024, backupCount=9)
fileLogger.setLevel(logging.ERROR)
fileLogger.setFormatter(formatter)
logging.getLogger('').addHandler(fileLogger)

logger = logging.getLogger('POCP')
logger.setLevel(logging.INFO)

########################################################################
# Download the the last year of POCP database, append to historical
# data->csv
########################################################################


class POCP(object):
    '''This is the POCP class'''
    def __init__(self, cmd_line, start_time=None, end_time=None):
        self.cmd_line = cmd_line
        self.start_time = start_time
        self.end_time = end_time
        self.update_time = None
        self.currDL = None

    #mappings
    def generation_type_map(self):
        with open(self.cmd_line.pocp_path + 'GT_map.json') as infile:
            self.GT_map = dict(json.load(infile))

    def island_map(self):
        with open(self.cmd_line.pocp_path + 'island_map.json') as infile:
            self.island_map = dict(json.load(infile))

    def mappings(self, df):
        logger.info('Applying generation type and island mappings')
        self.island_map()
        self.generation_type_map()
        def GIPer(row):
            """Get GIP from outage block when not in GIP/GXP column"""
            if row['GIP']== 'nan':
                row['GIP'] = row['Outage Block'][:3]
                return row
            else:
                return row
        df = df.apply(lambda x: GIPer(x), axis=1)
        df['Generation type'] = df.GIP.map(lambda x: self.GT_map[x])
        df['Island'] = df.GIP.map(lambda x: self.island_map[x])
        return df

    def dt_convert(self, x):
        if isinstance(x, str):
            date = x.split(' ')[0].split('-')
            time = x.split(' ')[1].split(':')
            return datetime(int(date[0]), int(date[1]), int(date[2]),
                            int(time[0]), int(time[1]), int(time[2]))
        else:
            return x

    def set_date_range(self):
        self.update_time = datetime.now()
        if self.start_time is None:
            self.strt = (self.update_time - timedelta(1 * 365))  # 6 mon<-
            self.start_time = self.strt.strftime('%d/%m/%Y')
        if self.end_time is None:
            self.endt = (self.update_time + timedelta(1 * 365))  # ~6 mon->
            self.end_time = self.endt.strftime('%d/%m/%Y')

    def pocp_login(self):

        logger.info("Login to POCP site")
        self.br = mechanize.Browser(factory=mechanize.RobustFactory())
        self.br.set_handle_robots(False)
        info_text = "Attempting to open " + self.cmd_line.pocp_host
        logger.info(info_text)
        self.br.open(self.cmd_line.pocp_host)
        self.br.select_form(nr=0)
        self.br['email'] = self.cmd_line.pocp_user
        self.br['password'] = self.cmd_line.pocp_pass
        self.br.submit()  # submit user name and password.
        logger.info("Logged in!")


    def download_pocp(self, legacy=True):  # Note: redspider limit<10000 rows

        logger.info('Getting POCP between ' + self.start_time + ' and ' + self.end_time)
        self.br.select_form(nr=0)  # select form
        self.br['start'] = self.start_time  # set start and end times from above
        self.br['end'] = self.end_time
        self.br.submit()  # submit the search/download for all POCP data
        if legacy:
            csv = self.br.click_link(text_regex=re.compile("Legacy"))
        else:
            csv = self.br.click_link(text_regex=re.compile("Download"))
        self.br.open(csv)
        bufferIO = StringIO()
        bufferIO.write(str(self.br.response().read()).decode('utf-8'))
        bufferIO.seek(0)
        if legacy:
            self.currDL = pd.read_csv(bufferIO, parse_dates=['Start', 'End', 'Last Modified'],
                          sep='\t', index_col=0)
        else:
            self.currDL = pd.read_csv(bufferIO, index_col=0, parse_dates=['Start', 'End', 'Last Modified'])


    def append_pocp(self, pocp):
        logger.info('Reading latest POCP data, and appending to pocp_all.csv')
        P_all = pd.read_csv(self.cmd_line.pocp_path + 'pocp_all.csv',
                            index_col=0)
        self.P = pd.concat([P_all, self.currDL])  # add latest download
        self.P['End'] = self.P.End.map(lambda x: p.dt_convert(x))  # datetimes
        self.P['Start'] = self.P.Start.map(lambda x: p.dt_convert(x))
        self.P['Last Modified'] = (
            self.P['Last Modified'].map(lambda x: p.dt_convert(x)))
        self.P = self.P.drop_duplicates()  # drop duplicates
        self.P.to_csv(self.cmd_line.pocp_path + 'pocp_all.csv')  # save updated
        return self.P

    def POCP_logic(self, outage_history=False):
        '''Main POCP grabber, with addition complex logic to try and get what
           we want, with a few assumptions thrown in for good measure...'''
        def POCP_get():
            def get(tdc):
                logger.info('Applying logic and returning all %s outages' % tdc)
                X = self.P[self.P.Category == tdc]
                # all outages between start and end including those that
                # have been cancelled
                Xbool = ((X['Start'] <= datetime.strptime(p.end_time, '%d/%m/%Y')) &
                         (X['End'] >= datetime.strptime(p.start_time, '%d/%m/%Y')))
                X = X[Xbool]
                #X['Duration'] = X.End - X.Start
                if tdc == 'Transmission':
                    del X['MW remaining']
                    del X['MW Loss']
                    del X['MV remaining']
                if tdc == 'Generation':
                    del X['Nature']

                del X['Category']
                return X
            T = get('Transmission')
            G = get('Generation')
            D = get('Direct Connection')
            if outage_history:
                if not T.empty:
                    T = (T.reset_index()
                         .set_index(['id', 'Last Modified'], drop=False)
                         .sortlevel(0))
                if not G.empty:
                    G = (G.reset_index()
                         .set_index(['id', 'Last Modified'], drop=False)
                         .sort(columns='MW Loss', ascending=False)
                         .sortlevel(0))
                if not D.empty:
                    D = (D.reset_index()
                         .set_index(['id', 'Last Modified'], drop=False)
                         .sortlevel(0))
            else:
                # This is what you should see in the current pocp
                # database that is now version controlled.
                if not T.empty:
                    T = T.set_index('Last Modified', append=True, drop=False).sortlevel(level=[0, 1])\
                         .groupby(level=0).last().set_index('Last Modified', append=True)
                if not G.empty:
                    G = G.set_index('Last Modified', append=True, drop=False).sortlevel(level=[0, 1])\
                         .groupby(level=0).last().set_index('Last Modified', append=True)
                if not D.empty:
                    D = D.set_index('Last Modified', append=True, drop=False).sortlevel(level=[0, 1])\
                         .groupby(level=0).last().set_index('Last Modified', append=True)
            return T, G, D

        def add_caned_after_start(df):
            # cancelled entries
            caned = df[df['Planning Status'] == 'Cancelled']
            caned = caned[  # if cancelled after Start time then keep
                caned.index.map(lambda x: x[1]) > caned.Start.tolist()]
            confirmed = df[df['Planning Status'] == 'Confirmed']
            tentative = df[df['Planning Status'] == 'Tentative']
            # Append confirmed outages with those that have been
            # cancelled after the outage window ended.
            df = confirmed.append(caned)
            # Also append all tentative outages, then sort.
            df = df.append(tentative).sort()
            df['GIP/GXPs'] = df['GIP/GXPs'].map(lambda x: str(x)[0: 3])
            #df['GIP/GXPs'][df['GIP/GXPs'] == '#N/'] = 'NAP'
            #df.replace(to_replace='#N/', value='NAP', inplace=True)
            df = df.rename(columns={'GIP/GXPs': 'GIP'})

            if 'MW Loss' in df.columns:
                df = df[df['MW Loss'] >= 0]
                df = df.ix[:, ['Start', 'End', 'MW Loss', 'Outage Block',
                               'GIP', 'Owner', 'Nature', 'Type', 'Duration',
                               'Planning Status']]
            else:
                df = df.ix[:, ['Start', 'End', 'Outage Block', 'GIP', 'Owner',
                               'Nature', 'Type', 'Duration', 'Planning Status']
                           ]

            df = df.fillna(0)
            return df

        T, G, D = POCP_get()  # get all history
        self.G = add_caned_after_start(G)
        self.T = add_caned_after_start(T)

    def today(self, df):
        current_bool = ((df['Start'] <= datetime.today()) &
                        (df['End'] >= datetime.today()))
        df = df[current_bool]
        df = df[df['Planning Status'] == 'Confirmed']
        df = df.drop_duplicates()
        df = df.groupby(level=0).tail(1)  # return the last modified entry...
        return df

    def now(self, df):
        current_bool = ((df['Start'] <= datetime.now()) &
                        (df['End'] >= datetime.now()))
        df = df[current_bool]
        df = df[df['Planning Status'] == 'Confirmed']
        df = df.drop_duplicates()
        df = df.groupby(level=0).tail(1)  # return the last modified entry...
        return df

    def save_metadata(self):
        logger.info('Dumping pocp meta data to metadata.json')
        with open(self.cmd_line.pocp_path + 'metadata.json', 'w') as outfile:
            json.dump({'updateTime': str(p.update_time.replace(microsecond=0)),
                       'startTime': p.start_time, 'endTime': p.end_time},
                      outfile)

    def save_generation_data(self):
        logger.info('Dumping pocp generation data to pocp_data_year.json')
        p.G.to_csv(self.cmd_line.pocp_path + 'pocp_data_year.json')

    def save_transmission_data(self):
        logger.info('Dumping pocp transmission data to pocp_transmission_data_year.json')
        p.T.to_csv(self.cmd_line.pocp_path + 'pocp_transmission_data_year.json')

    def main(self):
        outage_history = False
        self.set_date_range()  # set the start and end times
        self.pocp_login()
        self.download_pocp()  # download POCP over the data range
        # Append current download to the historic POCP data and save.
        self.append_pocp(self.currDL)
        self.POCP_logic(outage_history=outage_history)
        self.G = self.mappings(self.G)
        logger.info('Filtering current transmission outages')
        self.Tn = self.now(self.T)
        logger.info('Filtering current generation  outages')
        self.Gn = self.now(self.G)
        logger.info('Filtering todays transmission outages')
        self.Tt = self.today(self.T)
        logger.info('Filtering todays generation outages')
        self.Gt = self.today(self.G)
        self.save_metadata()
        self.save_generation_data()
        self.save_transmission_data()
        logger.info("pocp.py done!")

p = POCP(cmd_line)  # the POCP instance
p.main()

