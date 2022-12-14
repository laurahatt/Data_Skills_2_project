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
import spacy
nlp = spacy.load("en_core_web_sm")
import statsmodels.api as sm
from shiny import App, render, ui

path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'

#Load Urban Institute database of state child care (CCDF) policies
CCDF = os.path.join(path, 'data/CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)

#Load Urban Institute states shapefile
state_shp = os.path.join(path, 'UI_states.shp')
state_df  = geopandas.read_file(state_shp)
state_df = state_df.astype({'state_fips':'int'})

                            ###CCDF DATA CLEANING###

def record_selector(CCDF_full, sheet_name): 
    
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

def minhours_assembler(CCDF_full, sheet_name, state_df):
    minhours = record_selector(CCDF_full, 'EligCriteria')[['state_fips','EligMinWorkHours','EligMinHoursAmount']]
    minhours['Number_hours'] = minhours.apply (lambda row: min_hours_translator(row), axis=1)
    minhours['Category'] = minhours.apply (lambda row: min_hours_classifier(row), axis=1)
    minhours = minhours[['state_fips', 'Number_hours', 'Category']]
    minhours_geo = state_df.merge(minhours, on='state_fips', how='outer')
    return(minhours_geo)
    
minhours_geo = minhours_assembler(CCDF_full, 'EligCriteria', state_df)


#Job search as eligible activity
#at INITIAL application

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

def jobsearch_assembler(CCDF_full, sheet_name, state_df):
    jobsearch = record_selector(CCDF_full, 'EligCriteria')[['state_fips', 
                                                 'EligApproveActivityJobSearch',
                                                 'EligMaxTimeJobSearch', 
                                                 'EligMaxTimeJobSearchUnit',
                                                 'EligMaxTimeJobSearchTimeFrame']]
    jobsearch['Search_time'] = jobsearch.apply (lambda row: jobsearch_translator(row), axis=1)
    jobsearch = jobsearch.astype({'Search_time':'int'})
    jobsearch['Day_multiplier'] = jobsearch.apply (lambda row: jobsearch_day_multiplier(row), axis=1)    
    jobsearch['Days'] = jobsearch.apply (lambda row: jobsearch_day_generator(row), axis=1)
    jobsearch = jobsearch[['state_fips', 'Search_time', 'Day_multiplier', 'Days']]
    jobsearch_geo = state_df.merge(jobsearch, on='state_fips', how='outer')
    return(jobsearch_geo)


jobsearch_geo = jobsearch_assembler(CCDF_full, 'EligCriteria', state_df)

                    ###STATIC PLOTS###

def static_plot_maker_minhours():
    """Save and display chloropleth of minimum hours requirements"""
    
    fig, ax = plt.subplots(1, figsize=(5,5))
    
    ax = minhours_geo.plot(ax=ax, column='Category', categorical=True,  
                          cmap='RdBu_r',linewidth=.6, edgecolor='0.2',
                          legend=True, legend_kwds={'bbox_to_anchor':(1.1, 0),
                                                    'frameon':False,
                                                    'ncol':2}
                          )
    ax.set_title('Minimum Work Hour Requirements')
    ax.axis('off')
    
    legend_dict = {0: 'No minimum',
                   1: '15 to 19 hours per week',
                   2: '20 to 24 hours per week',
                   3: '25 to 29 hours per week',
                   4: '30 hours per week',
                   5: 'Other'}
    def replace_legend_items(legend, legend_dict):
        for txt in legend.texts:
            for k,v in legend_dict.items():
                if txt.get_text() == str(k):
                    txt.set_text(v)
    replace_legend_items(ax.get_legend(), legend_dict)

    #fig.savefig('images/minhours.png', bbox_inches="tight")
    #plt.show()
    
def static_plot_maker_jobsearch():
    """Save and display chloropleth of job search eligibility requirements"""
    
    fig, ax = plt.subplots(1, figsize=(5,5))
    
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes('bottom', size='10%', pad=0.1)

    ax = jobsearch_geo.plot(column='Days', categorical=False, 
                         cmap='RdBu', linewidth=.6, edgecolor='0.2',
                         ax=ax)
    ax.set_title('Days Eligible While Unemployed, \n (At Initial Application)')
    ax.axis('off')
    
    def cmap_maker(df, column, colors):
        range_min = df[column].min()
        range_max = df[column].max()
        cmap = plt.cm.ScalarMappable(
            norm = mcolors.Normalize(range_min, range_max),
            cmap = plt.get_cmap(colors))
        cmap.set_array([])
        return(cmap)
    
    colorbar(cmap_maker(jobsearch_geo, 'Days', 'RdBu'), cax=cax, orientation="horizontal")

    #fig.savefig('images/jobsearch.png', bbox_inches="tight")
    #plt.show()
 
static_plot_maker_minhours()
static_plot_maker_jobsearch()


                    ###NON-CCDF DATA CLEANING###
                                
#Mean family income
#https://fred.stlouisfed.org/series/MEHOINUSWAA646N

states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", 
          "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", 
          "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", 
          "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

def income_auto_downloader():
    """Use FRED API to download household income data for all states"""
    def code_maker(states):
        list_of_codes = []
        for st in states:
            fred_code = 'MEHOINUS' + st + 'A646N'
            list_of_codes.append(fred_code)
        return(list_of_codes)
    start = datetime.datetime(2019, 1, 1)
    end = datetime.datetime(2019, 1, 1)
    income = web.DataReader(code_maker(states), 'fred', start, end)
    return(income)

def income_assembler(income, state_df): 
    """Clean income df and merge with geometry"""
    income.columns = states
    income = income.transpose()
    income = income.reset_index()
    income.columns = ['state_abbv', 'med_inc']
    income = income.astype({'state_abbv':'string'})
    income_geo = state_df.merge(income, on='state_abbv', how='outer')
    return(income_geo)

income = income_auto_downloader() 
income_geo = income_assembler(income, state_df)


#Abortion access - table of gestational limits

url = 'https://www.guttmacher.org/state-policy/explore/state-policies-later-abortions'
response = requests.get(url)
abo_soup = BeautifulSoup(response.text, 'lxml')

def table_maker(abo_soup):
    """Convert soup object into table of unparsed text"""
    
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
    """Remove extraneous content and fill in missing limits"""  
    abo_df = abo_df_raw.applymap(lambda cell: cell.replace('\n', ''))
    abo_df = abo_df[abo_df['Statutory limit'] != 'TOTAL IN EFFECT']
    abo_df = abo_df.reset_index()
    return(abo_df)

def limit_filler(abo_df):
    
    partial_stat_limits = list(abo_df['Statutory limit'])
    full_stat_limits = []
    
    limits = abo_df['Statutory limit'].unique()
    def index_finder(limit_number):
        """Find the index of the first instance of the nth statutory limit"""
        limit_index  = abo_df[abo_df['Statutory limit'] == limits[limit_number]].index
        return(limit_index[0])
    
    for index, str in enumerate(partial_stat_limits):
        if index < index_finder(2): #Conception
            full_stat_limits.append(limits[0])
        elif index < index_finder(3): #6 weeks LMP
            full_stat_limits.append(limits[2])
        elif index == index_finder(3): #8 weeks LMP
            full_stat_limits.append(limits[3])
        elif index == index_finder(4): #12 weeks LMP
            full_stat_limits.append(limits[4])
        elif index < index_finder(6): #15 weeks LMP
            full_stat_limits.append(limits[5])
        elif index < index_finder(7): #18 weeks LMP
            full_stat_limits.append(limits[6])
        elif index < index_finder(8): #20 weeks LMP
            full_stat_limits.append(limits[7]) 
        elif index < index_finder(9): #22 weeks LMP
            full_stat_limits.append(limits[8]) 
        elif index < index_finder(10): #24 weeks LMP
            full_stat_limits.append(limits[9])
        elif index < index_finder(11): #Viability
            full_stat_limits.append(limits[10])
        else: #Third trimester
            full_stat_limits.append(limits[11])
        
    return(full_stat_limits)

def inactive_law_remover(abo_df):
    """Remove rows correponding to laws not currently active"""
    abo_df['Life_cl'] = abo_df['Life'].str.strip(' ')
    abo_df = abo_df[abo_df['Life_cl'] != '???'] #law permanently enjoined
    abo_df = abo_df[abo_df['Life_cl'] != '???'] #law temporarily enjoined
    abo_df = abo_df.reset_index()
    return(abo_df)

def state_name_cleaner(row):
    """Remove punctuation and special characters from state names"""
    new_row = row.translate(str.maketrans('', '', string.punctuation))
    new_row = new_row.replace('???', '').replace('???', '').replace('??', '').replace('??', '')
    new_row = new_row.rstrip()
    return(new_row)
 
def limit_cleaner(row):
    """Create ordered categorical variables, for plot legend"""
    
    if pd.isna(row): #States with no limit are not included in the original df
        return(0) #'No statutory limit'
    
    else:
        row = row.replace('\xa0', '')
        if row == 'Third trimester':
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
        elif row == 'Conception':
            return(9)
        else: 
            return('ERROR')

def abo_geo_assembler(abo_soup, state_df):
    """Parse, clean, and add geometry to abortion df"""
    abo_df = table_maker(abo_soup)
    abo_df = table_cleaner(abo_df)
    abo_df['stat_limit_1'] = limit_filler(abo_df)
    abo_df = abo_df[abo_df['State'] != '\xa0']
    abo_df = inactive_law_remover(abo_df)
    abo_df['state_name'] = abo_df['State'].apply(state_name_cleaner)
    #abo_df = abo_df[['Statutory limit', 'state_name']]
    abo_geo = state_df.merge(abo_df, on='state_name', how='outer')
    abo_geo['stat_limit_2'] = abo_geo['stat_limit_1'].apply(limit_cleaner)
    return(abo_geo)

abo_geo = abo_geo_assembler(abo_soup, state_df)



#https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas

#Sentiment analysis of governor speeches
#https://www.nasbo.org/resources/stateofthestates

speech_path = os.path.join(path, 'data/state_of_state_speeches.xlsx')
speeches = pd.read_excel(speech_path)

def sents_with_women(row):
    new_row = nlp(row)
    new_row = list(new_row.sents)
    new_row = [sent.text.replace('men and women', 'men') for sent in new_row]
    new_row = [sent for sent in new_row if 'women' in sent]
    return(new_row)

speeches['women'] = speeches['SPEECH'].apply(sents_with_women)
speeches['women_count'] = speeches['women'].apply(len)

#address these issues
speeches['women'][2]
speeches['women'][6]
speeches['women'][7]
speeches['women'][13] #cut
speeches['women'][17]
speeches['women'][20]
speeches['women'][21]
speeches['women'][22] #cut
speeches['women'][24] 
speeches['women'][27] #cut
speeches['women'][29] #cut
speeches['women'][31]
speeches['women'][34] #cut
speeches['women'][40]
speeches['women'][45]
speeches['women'][49] #cut

speeches.rename(columns={'STATE': 'state_abbv'}, inplace=True)
speeches_geo = state_df.merge(speeches, on='state_abbv', how='outer')


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
        ui.column(5, 
                  ui.input_select(id='comp',
                                  label='Choose an independent variable',
                                  choices= ['Median household income',
                                            'Abortion restrictions',
                                            'Mentions of women in State of the State']),
                  align='center'),
        ui.column(2, ui.h3(' '), align='center'),
        ui.column(5, 
                  ui.input_select(id='var',
                                  label='Choose a CCDF variable',
                                  choices= ['Minimum work hour requirements',
                                            'Duration of eligibility while unemployed']),
                  align='center')
        ),
    ui.row(
        ui.column(5, ui.output_plot('comp_mapper'), align='center'),
        ui.column(2, ui.output_text("rsquared_maker"), align='center'),
        ui.column(5, ui.output_plot('CCDF_mapper'), align='center')
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
            
            def replace_legend_items(legend, legend_dict):
                for txt in legend.texts:
                    for k,v in legend_dict.items():
                        if txt.get_text() == str(k):
                            txt.set_text(v)
            replace_legend_items(ax.get_legend(), legend_dict)
            
        else:
             
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            divider = make_axes_locatable(ax)
            cax = divider.append_axes('bottom', size='10%', pad=0.1)
    
            ax = jobsearch_geo.plot(column='Days', categorical=False, 
                                 cmap='RdBu', linewidth=.6, edgecolor='0.2',
                                 ax=ax)
            ax.set_title('Days Eligible While Unemployed, \n (At Initial Application)')
            
            def cmap_maker(df, column, colors):
                range_min = df[column].min()
                range_max = df[column].max()
                cmap = plt.cm.ScalarMappable(
                    norm = mcolors.Normalize(range_min, range_max),
                    cmap = plt.get_cmap(colors))
                cmap.set_array([])
                return(cmap)
            
            colorbar(cmap_maker(jobsearch_geo, 'Days', 'RdBu'), cax=cax, orientation="horizontal")

        ax.axis('off')
        
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
            
            def cmap_maker(df, column, colors):
                range_min = df[column].min()
                range_max = df[column].max()
                cmap = plt.cm.ScalarMappable(
                    norm = mcolors.Normalize(range_min, range_max),
                    cmap = plt.get_cmap(colors))
                cmap.set_array([])
                return(cmap)
            
            colorbar(cmap_maker(income_geo, 'med_inc', 'RdBu_r'), cax=cax, orientation="horizontal")
        
        elif input.comp() == 'Abortion restrictions':
            
            ax = abo_geo.plot(column='stat_limit_2', categorical=True, cmap='RdBu_r', 
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
        
        else:
            
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            divider = make_axes_locatable(ax)
            cax = divider.append_axes('bottom', size='10%', pad=0.1)
    
            ax = speeches_geo.plot(column='women_count', categorical=False, 
                                 cmap='RdBu', linewidth=.6, edgecolor='0.2',
                                 ax=ax)
            ax.set_title('Mentions of women in State of the State address')
            
            def cmap_maker(df, column, colors):
                range_min = df[column].min()
                range_max = df[column].max()
                cmap = plt.cm.ScalarMappable(
                    norm = mcolors.Normalize(range_min, range_max),
                    cmap = plt.get_cmap(colors))
                cmap.set_array([])
                return(cmap)
            
            colorbar(cmap_maker(speeches_geo, 'women_count', 'RdBu_r'), cax=cax, orientation="horizontal")     
        
        ax.axis('off')
        return ax
    
    @output
    @render.text
    def rsquared_maker():
        
        if input.var() == 'Minimum work hour requirements':
            return('Categorical variable: No regression')
        
        elif input.comp() == 'Abortion restrictions':
            return('Categorical variable: No regression')
        
        else:
            x_df_dict = {'Median household income': income_geo,
                         'Mentions of women in State of the State': speeches_geo}
            x_var_dict = {'Median household income': 'med_inc',
                         'Mentions of women in State of the State': 'women_count'}
            x_df = x_df_dict[input.comp()]
            x_var = x_var_dict[input.comp()]
            x = x_df[x_var].tolist()
            x = sm.add_constant(x)
            
            y_df_dict = {'Duration of eligibility while unemployed': jobsearch_geo}
            y_var_dict = {'Duration of eligibility while unemployed': 'Days'}
            y_df = y_df_dict[input.var()]
            y_var = y_var_dict[input.var()]
            y = y_df[y_var].tolist()
            
            result = sm.OLS(y, x).fit()
            rsq = result.rsquared.round(5)
            
            title = 'R-Squared Value: '
            full_text = title + str(rsq)
            
            return(full_text)
        
app = App(app_ui, server)

