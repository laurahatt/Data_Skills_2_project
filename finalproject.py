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

minhours = record_selector('EligCriteria')[['state_fips',
                                            'EligMinWorkHours',
                                            'EligMinHoursAmount',
                                            'EligMinHoursAmount_NOTES']]

def min_hours_interpreter(row):
    
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

minhours['Interpretation'] = minhours.apply (lambda row: min_hours_interpreter(row), axis=1)
minhours = minhours[['state_fips', 'Interpretation']]


def min_hours_classifier(row):
    """Create categorical variable"""
    
    if row['Interpretation'] == 0:
        return(0)
    elif row['Interpretation'] >= 15 and row['Interpretation'] < 20:
        return(1)
    elif row['Interpretation'] >= 20 and row['Interpretation'] < 25:
        return(2)
    elif row['Interpretation'] >= 25 and row['Interpretation'] < 30:
        return(3)
    elif row['Interpretation'] == 30:
        return(4)
    elif row['Interpretation'] == -3:
        return(5)
    else:
        return(6)

minhours['Category'] = minhours.apply (lambda row: min_hours_classifier(row), axis=1)

minhours_geo = state_df.merge(minhours, on='state_fips', how='outer')

#plot

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


#Reimbursement rates in each state
#Note that I'm restricting to "majority rec", 
#which includes only one provider type (usually a type of center)
#only one county per state, if multiple
#only rate for first child in a family
#not considering special rates, such as special needs, etc.
#also note year - this is FFY2020, I believe


reimburse = record_selector('ReimburseRates')[['state_fips', 
                                               'ReimburseHourly1']]

reimburse = pd.read_excel(CCDF_full, 'ReimburseRates')
reimburse = reimburse[reimburse['MajorityRec'] == -1]
reimburse = reimburse[reimburse['EndDat'] == '9999/12/31']
reimburse = reimburse[['State', 'County', 'ReimburseRatesProviderType', 
                       'ReimburseHourly1', 'ReimburseDailyFull1', 
                       'ReimburseDailyPart1','ReimburseWeeklyFull1', 
                       'ReimburseWeeklyPart1', 'ReimburseMonthlyFull1', 
                       'ReimburseMonthlyPart1', 'Notes']]

#Multipliers
reimburse_policies = pd.read_excel(CCDF_full, 'ReimbursePolicies')
reimburse_policies = reimburse_policies[reimburse_policies['MajorityRec'] == -1]
reimburse_policies = reimburse_policies[reimburse_policies['EndDat'] == '9999/12/31']
reimburse_policies = reimburse_policies[['State', 'ReimburseMultiplier']]

#Merge rates and multipliers
reimburse_full = reimburse_policies.merge(reimburse, on='State', how='outer')

#Calculate monthly rate
#now calculate actual rate
def rate_calculator(row):
    
    if row['ReimburseMultiplier'] == 1:
        return('monthly')
    elif row['ReimburseMultiplier'] > 1 and row['ReimburseMultiplier'] <= 5:
        return('weekly')
    elif row['ReimburseMultiplier'] > 5 and row['ReimburseMultiplier'] <= 30:
        return('daily')
    elif row['ReimburseMultiplier'] >30 and row['ReimburseMultiplier'] <= 240:
        return('hourly')
    else:
        return('what?')
    
 
reimburse_full['FinalRate'] = reimburse_full.apply (lambda row: rate_calculator(row), axis=1)   
reimburse_full




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

