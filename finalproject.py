#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 14 10:18:52 2022

@author: laurahatt
"""

import os
import pandas as pd
import geopandas
import matplotlib.pyplot as plt
pd.set_option('display.max_columns', None)
import pandas_datareader.data as web
import datetime
from matplotlib.pyplot import colorbar
import matplotlib.colors as mcolors
from bs4 import BeautifulSoup
import requests
import string
from shiny import App, render, ui

path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'

#Load Urban Institute database of state child care policies
CCDF = os.path.join(path, 'CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)

#Load Urban Institute states shapefile
state_shp = os.path.join(path, 'UI_states.shp')
state_df  = geopandas.read_file(state_shp)
state_df = state_df.astype({'state_fips':'int'})

                            ###CCDF DATA CLEANING###

#Select relevant policy categories within policy database

def record_selector(sheet_name): 
    
    """Select and clean relevant sheet of CCDF policy database"""
    sheet = pd.read_excel(CCDF_full, sheet_name)
    sheet = sheet[sheet['MajorityRec'] == -1]
    sheet.rename(columns={'State': 'state_fips'}, inplace=True)
    sheet = sheet[sheet['state_fips'] < 60]
    
    """For each state, select current record (marked 999/12/31) or most recent record."""
    current_records = pd.DataFrame()
    list_of_states = list(sheet['state_fips'].unique())
    for state in list_of_states:
        df = sheet[sheet['state_fips'] == state]
        if '9999/12/31' in list(df['EndDat']):
            new_row = df[df['EndDat'] ==  '9999/12/31']
            current_records = pd.concat([current_records, new_row], axis=0, ignore_index=True)
        else:
            latest_date = df['EndDat'].apply(pd.to_datetime).max()
            new_row = df.loc[df['EndDat'] == latest_date.strftime('%Y/%m/%d')] 
            current_records = pd.concat([current_records, new_row], axis=0, ignore_index=True)
    
    return(current_records)

        
#Minimum hours of work to be eligible
#Focusing on a single-parent household
#and minimum hours for at least part-time care 

def min_hours_translator(row):
    """Translate codes into number of hours per week"""
    if row['EligMinWorkHours'] == 1:
        return(0)
    elif row['EligMinWorkHours'] == 2 or row['EligMinWorkHours'] == 3 :
        if row['EligMinHoursAmount'] >= 0:
            return(row['EligMinHoursAmount'])
        elif row['EligMinHoursAmount'] == -3:
            return(-3) # This category is "Other"
        else:
            return('There is a problem here')
    else:
        return('There is a problem here') 

def min_hours_classifier(row):
    """Translate number of hours into categorical variable"""
    if row['Number_hours'] == 0:
        return(0) #No minimum
    elif row['Number_hours'] >= 15 and row['Number_hours'] < 20:
        return(1) #15-19 hours/week
    elif row['Number_hours'] >= 20 and row['Number_hours'] < 25:
        return(2) #20-24 hours/week
    elif row['Number_hours'] >= 25 and row['Number_hours'] < 30:
        return(3) #25-29 hours/week
    elif row['Number_hours'] == 30:
        return(4) #30 hours/week
    elif row['Number_hours'] == -3:
        return(5) #"Other"
    else:
        return(6)

#I bet I could organize these in a function too
minhours = record_selector('EligCriteria')[['state_fips','EligMinWorkHours','EligMinHoursAmount']]
minhours['Number_hours'] = minhours.apply (lambda row: min_hours_translator(row), axis=1)
minhours['Category'] = minhours.apply (lambda row: min_hours_classifier(row), axis=1)
minhours = minhours[['state_fips', 'Number_hours', 'Category']]
minhours_geo = state_df.merge(minhours, on='state_fips', how='outer')


#Job search as eligible activity
#at INITIAL application

#Can I consolidate these four functions into one?
def jobsearch_translator(row):
    """Translate codes into time"""
    if row['EligApproveActivityJobSearch'] == 2 or row['EligApproveActivityJobSearch'] == 3:
        return(0) #Job search not eligible at initial application
    elif row['EligApproveActivityJobSearch'] == 1:
        if row['EligMaxTimeJobSearch'] >= 0:
            return(row['EligMaxTimeJobSearch'])
        elif row['EligMaxTimeJobSearch'] == -1:
            return(-1) # Through end of eligibility period
        elif row['EligMaxTimeJobSearch'] == -2:
            return(-2) # No limit
        elif row['EligMaxTimeJobSearch'] == -3:
            return(-3) # Other 
        elif row['EligMaxTimeJobSearch'] == -4:
            return(-4) # NA
        elif row['EligMaxTimeJobSearch'] == -5:
            return(-5) # Not in manual
        else:
            return('Problem A')
    else:
        return('-6')  #Other  - New York

def jobsearch_day_multiplier(row):
    """Translate codes into time"""
    if row['Search_time'] == 0:
        return(0) #Job search not eligible at initial application
    elif row['Search_time'] > 0:
        if row['EligMaxTimeJobSearchUnit'] == 2:
            return(1) #Units are already in days
        elif row['EligMaxTimeJobSearchUnit'] == 3:
            return(7) #Units are currently in weeks
        elif row['EligMaxTimeJobSearchUnit'] == 4:
            return(30) #Units are currently in months
        else:
            return('Problem A')
    else:
        return(row['Search_time'])

def jobsearch_day_generator(row):
    if row['Search_time'] == 0:
        return(0) #Job search not eligible at initial application
    elif row['Search_time'] > 0:
        return(row['Search_time'] * row['Day_multiplier'])
    elif row['Search_time'] == -1:
        return(365) #Special case for California
    elif row['Search_time'] == -6:
        return(180) #Special case for New York
    else:
        return('Problem')
    
def jobsearch_classifier(row):
    """Translate number of hours into categorical variable"""
    if row['Days'] == 0:
        return(0) #No minimum
    elif row['Days'] == 30:
        return(1) #30 days
    elif row['Days'] >= 84 and row['Days'] < 92:
        return(2) #12 weeks or 3 months
    elif row['Days'] == 180:
        return(3) #6 months
    else: 
        return(4) #one year

jobsearch = record_selector('EligCriteria')[['state_fips', 
                                             'EligApproveActivityJobSearch',
                                             'EligMaxTimeJobSearch', 
                                             'EligMaxTimeJobSearchUnit',
                                             'EligMaxTimeJobSearchTimeFrame']]


jobsearch['Search_time'] = jobsearch.apply (lambda row: jobsearch_translator(row), axis=1)
jobsearch = jobsearch.astype({'Search_time':'int'})
jobsearch['Day_multiplier'] = jobsearch.apply (lambda row: jobsearch_day_multiplier(row), axis=1)    
jobsearch['Days'] = jobsearch.apply (lambda row: jobsearch_day_generator(row), axis=1)
jobsearch['Category'] = jobsearch.apply (lambda row: jobsearch_classifier(row), axis=1)
jobsearch = jobsearch[['state_fips', 'Search_time', 'Day_multiplier', 'Days', 'Category']]

jobsearch_geo = state_df.merge(jobsearch, on='state_fips', how='outer')


#Income eligibility thresholds for family of 2
#whether a family with a CPS case is exempt from copayments


                    ###NON-CCDF DATA CLEANING###
                    
                    
#Mean family income
#ex - https://fred.stlouisfed.org/series/MEHOINUSWAA646N

states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", 
          "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", 
          "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", 
          "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

def code_maker(states):
    list_of_codes = []
    for st in states:
        fred_code = 'MEHOINUS' + st + 'A646N'
        list_of_codes.append(fred_code)
    return(list_of_codes)

start = datetime.datetime(2019, 1, 1)
end = datetime.datetime(2019, 1, 1)
income = web.DataReader(code_maker(states), 'fred', start, end)

income.columns = states
income = income.transpose()
income = income.reset_index()
income.columns = ['state_abbv', 'med_inc']
income = income.astype({'state_abbv':'string'})

income_geo = state_df.merge(income, on='state_abbv', how='outer')


#Abortion access - table of gestational limits

url = 'https://www.guttmacher.org/state-policy/explore/state-policies-later-abortions'
response = requests.get(url)
abo_soup = BeautifulSoup(response.text, 'lxml')

def table_maker(soup):
    
    abo_table = abo_soup.find('table')
    
    headers1 = [tr.text for tr in abo_table.find_all('tr')[1].find_all('p')]
    headers2 = [tr.text for tr in abo_table.find_all('tr')[2].find_all('p')]
    headers2 = [tr.replace('\n', ' ').replace('\t', '') for tr in headers2]
    abo_df_raw = pd.DataFrame(columns = headers1[:-1] + headers2)
    
    num_rows = list(range(3, len(abo_table.find_all('tr')), 1))
    for row in num_rows:
        new_row = [val.text for val in abo_table.find_all('tr')[row].find_all('td')]
        abo_df_raw.loc[len(abo_df_raw)] = new_row
    
    return(abo_df_raw)
    
 
def table_cleaner(abo_df_raw):
    
    """Clean up extraneous HTML and summary rows"""
    abo_df = abo_df_raw.applymap(lambda cell: cell.replace('\n', ''))
    abo_df = abo_df[abo_df['Statutory limit'] != 'TOTAL IN EFFECT']
    abo_df = abo_df.reset_index()
   
    """Fill in Statutory Limit where it is missing"""
    limits = abo_df['Statutory limit'].unique()
    
    def index_finder(limit_number):
        """Find the index of the first instance of the nth statutory limit"""
        limit_index  = abo_df[abo_df['Statutory limit'] == limits[limit_number]].index
        return(limit_index[0])
    
    for row in list(range(0, len(abo_df))):
        
        if row < index_finder(2): #Conception
            abo_df.loc[(abo_df.index < index_finder(2)), 'Statutory limit'] = limits[0]
        
        elif row < index_finder(3): #6 weeks LMP
            abo_df['Statutory limit'][row] = limits[2]
            #tb1.loc[12:18, 'Statutory limit'] = 'placeholder'
            
        elif row == index_finder(3): #8 weeks LMP
            abo_df['Statutory limit'][row] = limits[3]
            
        elif row == index_finder(4): #12 weeks LMP
            abo_df['Statutory limit'][row] = limits[4]
        
        elif row < index_finder(6): #15 weeks LMP
            abo_df['Statutory limit'][row] = limits[5]
        
        elif row < index_finder(7): #18 weeks LMP
            abo_df['Statutory limit'][row] = limits[6]
        
        elif row < index_finder(8): #20 weeks LMP
            abo_df['Statutory limit'][row] = limits[7]
            
        elif row < index_finder(9): #22 weeks LMP
            abo_df['Statutory limit'][row] = limits[8]
            
        elif row < index_finder(10): #24 weeks LMP
            abo_df['Statutory limit'][row] = limits[9]
        
        elif row < index_finder(11): #Viability
            abo_df['Statutory limit'][row] = limits[10]
        
        else: #Third trimester
            pass
    
    abo_df = abo_df[abo_df['State'] != '\xa0']
    
    return(abo_df)

def inactive_law_remover(abo_df):
    abo_df['Life'] = abo_df['Life'].str.strip(' ')
    abo_df = abo_df[abo_df['Life'] != '▼'] #law permanently enjoined
    abo_df = abo_df[abo_df['Life'] != '▽'] #law temporarily enjoined
    abo_df = abo_df.reset_index()
    return(abo_df)

def state_name_cleaner(row):
    new_row = row.translate(str.maketrans('', '', string.punctuation))
    new_row = new_row.replace('‡', '').replace('†', '').replace('Ɵ', '').replace('β', '')
    new_row = new_row.rstrip()
    return(new_row)
 
abo_df = table_cleaner(table_maker(abo_soup))
abo_df = inactive_law_remover(abo_df)
abo_df['state_name'] = abo_df['State'].apply(state_name_cleaner)
abo_df = abo_df[['Statutory limit', 'state_name']]

abo_geo = state_df.merge(abo_df, on='state_name', how='outer')

def nan_replacer(row):
     if pd.isna(row):
         return('No statutory limit')
     else:
         return(row)
 
abo_geo['stat_limit'] = abo_geo['Statutory limit'].apply(nan_replacer).apply(lambda x: x.replace('\xa0', ''))


def limit_classifier(row):
    """Translate statutory limits into ordinal categorical variable"""
    if row == 'No statutory limit':
        return(0) 
    elif row == 'Third trimester':
        return(1) 
    elif row == 'Viability':
        return(2) 
    elif row == '24 weeks LMP':
        return(3)
    elif row == '22 weeks LMP':
        return(4)
    elif row == '20 weeks LMP':
        return(5)
    elif row == '18 weeks LMP':
        return(6)
    elif row == '15 weeks LMP':
        return(7)
    elif row == '6 weeks LMP':
        return(8)
    else: 
        return(9) #Conception

abo_geo['stat_limit_cat'] = abo_geo['stat_limit'].apply(limit_classifier)

#https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas

#Sentiment analysis of governor speeches
#https://www.nasbo.org/mainsite/resources/stateofthestates/sos-summaries
#https://www.nasbo.org/resources/stateofthestates



#Cost of childcare

#Measure of state progressiveness?
#maybe 2020 federal election results



                    ###SHINY###

app_ui = ui.page_fluid(
    ui.row(
        ui.column(12, 
                  ui.h1('Final Project'), 
                  align='center')
        ),
    ui.row(
        ui.column(12, 
                  ui.h4('Created by Laura Hatt'), 
                  align='center')
        ),
    ui.row(ui.column(12, ui.h3(' '))),
    ui.row(ui.column(12, ui.h3(' '))),
    ui.row(
        ui.column(6, 
                  ui.input_select(id='var',
                                  label='Choose a CCDF variable',
                                  choices= ['Minimum work hour requirements',
                                            'Duration of eligibility while unemployed']),
                  align='center'),
        ui.column(6, 
                  ui.input_select(id='comp',
                                  label='Choose a complementary variable',
                                  choices= ['Median household income',
                                            'Abortion restrictions']),
                  align='center')
        ),
    ui.row(
        ui.column(6, ui.output_plot('CCDF_mapper'), align='center'),
        ui.column(6, ui.output_plot('comp_mapper'), align='center')
        ),
    ui.row(
        ui.column(6, 
                  ui.h6('Data from XX'), 
                  align='center'),
        ui.column(6, 
                  ui.h6('Data from YY'), 
                  align='center')
        )
)


def server(input, output, session):

    @output
    @render.plot
    def CCDF_mapper():
        #Can I set "other" to gray?
        fig, ax = plt.subplots(1, figsize=(5,5))
        
        if input.var() == 'Minimum work hour requirements':
            ax = minhours_geo.plot(column='Category', categorical=True, cmap='RdBu_r', 
                                  linewidth=.6, edgecolor='0.2',
                                  legend=True, 
                                  legend_kwds={'bbox_to_anchor':(1, 0), 
                                               'frameon':False,
                                               'ncol':2}, 
                                  ax=ax)
            ax.set_title('Minimum Work Hour Requirements')
            legend_dict = {0: 'No minimum',
                           1: '15 to 19 hours per week',
                           2: '20 to 24 hours per week',
                           3: '25 to 29 hours per week',
                           4: '30 hours per week',
                           5: 'Other'}
        else:
             ax = jobsearch_geo.plot(column='Category', categorical=True, cmap='RdBu', 
                               linewidth=.6, edgecolor='0.2',
                               legend=True, 
                               legend_kwds={'bbox_to_anchor':(0.8, 0), 
                                            'frameon':False,
                                            'ncol':2}, 
                               ax=ax)
             ax.set_title('Duration of Eligibility While Unemployed, \n (At Initial Application)')
             legend_dict = {0: 'Not eligible',
                            1: 'One month',
                            2: 'Three months',
                            3: 'Six months',
                            4: 'One year'}

        ax.axis('off')
        
        def replace_legend_items(legend, legend_dict):
            for txt in legend.texts:
                for k,v in legend_dict.items():
                    if txt.get_text() == str(k):
                        txt.set_text(v)
        replace_legend_items(ax.get_legend(), legend_dict)
        
        return ax
    
    @output
    @render.plot
    def comp_mapper():
        
        fig, ax = plt.subplots(1, figsize=(5,5))
        
        if input.comp() == 'Median household income':
            
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            divider = make_axes_locatable(ax)
            cax = divider.append_axes('bottom', size='10%', pad=0.1)
    
            ax = income_geo.plot(column='med_inc', categorical=False, 
                                 cmap='RdBu', linewidth=.6, edgecolor='0.2',
                                 ax=ax)
            ax.set_title('Median Household Income')
            
            def cmap_maker(column, colors):
                range_min = income[column].min()
                range_max = income[column].max()
                cmap = plt.cm.ScalarMappable(
                    norm = mcolors.Normalize(range_min, range_max),
                    cmap = plt.get_cmap(colors))
                cmap.set_array([])
                return(cmap)
            
            colorbar(cmap_maker('med_inc', 'RdBu_r'), cax=cax, orientation="horizontal")
        
        else:
            
            ax = abo_geo.plot(column='stat_limit_cat', categorical=True, cmap='RdBu_r', 
                                  linewidth=.6, edgecolor='0.2',
                                  legend=True, 
                                  legend_kwds={'bbox_to_anchor':(1, 0), 
                                               'frameon':False,
                                               'ncol':3}, 
                                  ax=ax)
            ax.set_title('State statutory limits on abortion')
            
            legend_dict = {0: 'No statutory limit',
                           1: 'Third trimester',
                           2: 'Viability',
                           3: '24 weeks LMP',
                           4: '22 weeks LMP',
                           5: '20 weeks LMP',
                           6: '18 weeks LMP',
                           7: '15 weeks LMP',
                           8: '6 weeks LMP',
                           9: 'Conception'}
            
            def replace_legend_items(legend, legend_dict):
                for txt in legend.texts:
                    for k,v in legend_dict.items():
                        if txt.get_text() == str(k):
                            txt.set_text(v)
            replace_legend_items(ax.get_legend(), legend_dict)
            
            pass
        
        ax.axis('off')
        return ax
        

app = App(app_ui, server)








