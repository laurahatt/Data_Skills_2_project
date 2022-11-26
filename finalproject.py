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
from datetime import strftime
pd.set_option('display.max_columns', None)

#Load Urban Institute database of state child care policies
path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'
CCDF = os.path.join(path, 'CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)

#Load Urban Institute states shapefile
state_shp = os.path.join(path, 'UI_states.shp')
state_df  = geopandas.read_file(state_shp)
state_df = state_df.astype({'state_fips':'int'})

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

#plot
#Need to turn this into a function

fig, ax = plt.subplots(1, figsize=(5,5))
minhours_geo.plot(column='Category', categorical=True, cmap='YlGn', 
                  linewidth=.6, edgecolor='0.2',
                  legend=True, 
                  legend_kwds={'bbox_to_anchor':(1.6, 0.9), 'frameon':False}, 
                  ax=ax)

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

ax.axis('off')
ax.set_title('State Minimum Work Hour Requirements (2019)')

#Can I set "other" to gray?
#Can I center the title to be over the legend as well?


#Job search as eligible activity
#at INITIAL application


#(0) NA
#(1) Yes, for initial and continuing eligibility
#(2) Yes, only for continuing eligibility
#(3) No

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

#OK - now plot!

fig, ax = plt.subplots(1, figsize=(5,5))
jobsearch_geo.plot(column='Category', categorical=True, cmap='YlGn', 
                  linewidth=.6, edgecolor='0.2',
                  legend=True, 
                  legend_kwds={'bbox_to_anchor':(1.6, 0.9), 'frameon':False}, 
                  ax=ax)
legend_dict = {0: 'None',
               1: 'One month',
               2: 'Three months',
               3: 'Six months',
               4: 'One year'}
def replace_legend_items(legend, legend_dict):
    for txt in legend.texts:
        for k,v in legend_dict.items():
            if txt.get_text() == str(k):
                txt.set_text(v)
replace_legend_items(ax.get_legend(), legend_dict)

ax.axis('off')
ax.set_title('job search')



#(0) NA
#(2) Days
#(3) Weeks
#(4) Months



#average days in a month: average is 30.437


#Income eligibility thresholds for family of 2
#whether a family with a CPS case is exempt from copayments


#Background checks of unlicensed home-based providers
#note that some states may appear to have no backchecks,
#but really they just have no unlicensed home-based providers





#If I were going to go forward, I'd get def of regions, 
#link to region shapefile, and then make chloropleth



#Other maps

#Sentiment analysis of governor speeches
#https://www.nasbo.org/mainsite/resources/stateofthestates/sos-summaries
#https://www.nasbo.org/resources/stateofthestates

#Abortion access

#Cost of childcare

#Measure of state progressiveness?

#Mean family income
#https://fred.stlouisfed.org/release/tables?eid=257197&rid=110

